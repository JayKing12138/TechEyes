# Token认证问题修复 🔐

## 问题诊断

从后端日志发现：
```
POST /api/auth/login status=200  ✅ 登录成功
GET /api/projects status=401     ❌ 访问项目列表失败（未授权）
```

**根本原因：** 前端axios拦截器中的token没有正确更新。

## 问题分析

### 原来的实现（有问题）

**frontend/src/services/api.ts:**
```typescript
// ❌ 问题：authToken只在模块加载时初始化一次
let authToken = localStorage.getItem('techeyes_auth_token') || ''

export const setAuthToken = (token: string | null) => {
  authToken = token || ''  // 只更新了模块变量
}

api.interceptors.request.use((config) => {
  if (authToken) {  // 使用可能过时的authToken变量
    config.headers.Authorization = `Bearer ${authToken}`
  }
})
```

**问题场景：**
1. 用户首次访问，`authToken` 初始化为空字符串
2. 用户登录，调用 `setAuthToken(token)`，更新了 `authToken` 变量
3. 但如果页面刷新，`api.ts` 模块重新加载
4. `authToken` 重新从 `localStorage` 读取
5. 理论上应该能读到token，但实践中可能有时序问题

**核心问题：** 依赖一个模块级别的可变状态（`authToken`），而不是每次请求时动态获取最新值。

## 修复方案

### 改进后的实现

**frontend/src/services/api.ts:**
```typescript
const TOKEN_KEY = 'techeyes_auth_token'

export const setAuthToken = (token: string | null) => {
  // ✅ 直接操作localStorage，不维护模块变量
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

api.interceptors.request.use((config) => {
  // ✅ 每次请求时从localStorage读取最新token
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

**优点：**
- ✅ 每次请求都获取最新token，无状态问题
- ✅ 页面刷新后token仍然有效
- ✅ 多个tab页token同步

### 简化 auth store

**frontend/src/stores/auth.ts:**
```typescript
// ❌ 删除不需要的 initialize() 方法
actions: {
  // initialize() {  // 不再需要
  //   setAuthToken(this.token || null)
  // },

  async login(username: string, password: string) {
    const data = await loginUser({ username, password })
    this.token = data.access_token
    this.user = data.user
    
    localStorage.setItem(TOKEN_KEY, this.token)
    localStorage.setItem(USER_KEY, JSON.stringify(this.user))
    setAuthToken(this.token)  // 虽然现在这个调用是冗余的，但保持兼容性
    return data
  }
}
```

**frontend/src/main.ts:**
```typescript
// ❌ 删除不需要的 initialize() 调用
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
// authStore.initialize()  // 不再需要
app.use(router)
app.mount('#app')
```

## 后端增强调试

**backend/services/auth_service.py:**

添加详细的调试日志，便于诊断token验证问题：

```python
async def get_current_user(...):
    logger.debug(f"[Auth] Authorization header: {authorization}")
    
    if not authorization:
        logger.debug("[Auth] 无Authorization header")
        return None
    
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    logger.debug(f"[Auth] Token: {token[:20]}...")
    
    user_info = verify_access_token(token)
    if not user_info:
        logger.debug("[Auth] Token验证失败")
        return None
    
    logger.debug(f"[Auth] 用户认证成功: {user.username}")
    return {"id": user.id, "username": user.username}
```

## 修改文件清单

### 前端修改
1. **frontend/src/services/api.ts**
   - 删除模块级 `authToken` 变量
   - 修改 `setAuthToken()` 直接操作localStorage
   - 修改拦截器每次从localStorage读取token

2. **frontend/src/stores/auth.ts**
   - 删除 `initialize()` 方法

3. **frontend/src/main.ts**
   - 删除 `authStore.initialize()` 调用

### 后端修改
1. **backend/services/auth_service.py**
   - 在 `get_current_user()` 中添加详细调试日志

## 测试步骤

### 方式1: 使用自动化测试脚本
```bash
chmod +x test_auth_fix.sh
./test_auth_fix.sh
```

### 方式2: 手动测试
```bash
# 1. 未登录访问（应该401）
curl http://localhost:8000/api/projects

# 2. 登录获取token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
# 复制返回的 access_token

# 3. 使用token访问（应该200）
curl http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 方式3: 浏览器测试
1. 打开浏览器开发者工具（F12）
2. 访问项目列表页面（未登录）
3. 在Network标签中查看 `/api/projects` 请求
4. 应该看到401错误
5. 登录用户
6. 再次访问项目列表页面
7. Network中应该看到：
   ```
   Request Headers:
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhb...
   ```
8. 响应状态码应该是200
9. 刷新页面，仍然能正常访问（验证token持久化）

## 预期效果

### 修复前 ❌
```
用户登录 → localStorage有token
访问项目列表 → 没有发送Authorization header
后端返回401 → 前端显示未授权
```

### 修复后 ✅
```
用户登录 → localStorage有token
访问项目列表 → 自动从localStorage读取token并发送
后端验证token成功 → 返回该用户的项目列表
页面刷新 → token仍然有效，正常访问
```

## 后端日志示例

### 修复后应该看到：
```
[REQ] POST /api/auth/login
[Auth] 用户登录: admin
[RES] POST /api/auth/login status=200

[REQ] GET /api/projects
[Auth] Authorization header: Bearer eyJ0eXAiOiJKV1Qi...
[Auth] Token: eyJ0eXAiOiJKV1Qi...
[Auth] Token验证成功，用户ID: 1
[Auth] 用户认证成功: admin
[RES] GET /api/projects status=200
```

### 如果仍然401，日志会显示：
```
[REQ] GET /api/projects
[Auth] Authorization header: None
[Auth] 无Authorization header
[RES] GET /api/projects status=401
```

或者：

```
[REQ] GET /api/projects
[Auth] Authorization header: Bearer invalid_token
[Auth] Token: invalid_token
[Auth] Token验证失败
[RES] GET /api/projects status=401
```

## 常见问题排查

### Q1: 登录后仍然401
**排查步骤：**
1. 打开浏览器控制台
2. 检查 `localStorage.getItem('techeyes_auth_token')`
3. 如果有值，检查Network中的请求是否带了Authorization header
4. 如果没有Authorization header，可能是浏览器缓存问题，强制刷新（Ctrl+Shift+R）

### Q2: 后端日志显示"Token验证失败"
**可能原因：**
- Token已过期（超过24小时）
- SECRET_KEY不匹配（后端重启后可能改变）
- Token格式错误

**解决方法：**
重新登录获取新token

### Q3: 刷新页面后401
**可能原因：**
- localStorage被清空
- 浏览器隐私模式下localStorage可能不保存

**解决方法：**
重新登录

## 技术要点

### 为什么不用模块变量？
JavaScript模块在首次导入时执行一次，之后会被缓存。但是：
- 模块变量的值在初始化后可能不会同步更新
- 页面刷新会重新加载模块，可能导致时序问题
- 多个组件同时导入时，初始化顺序不确定

### 为什么每次请求都读localStorage？
- localStorage操作很快（同步读取）
- 确保每次都是最新值
- 避免状态不一致问题
- 支持多tab页同步（一个tab登录，其他tab也能用）

### setAuthToken还有用吗？
现在的实现中，`setAuthToken()` 只是localStorage的包装器，理论上可以直接操作localStorage。但保留它有几个好处：
- API兼容性（代码不需要大改）
- 以后可能扩展（如发送事件通知）
- 代码更清晰（明确是在设置认证token）

## 总结

✅ **核心修复：** 从"依赖可变模块状态"改为"每次动态读取localStorage"

✅ **架构改进：** 更简单、更可靠、更易维护

✅ **调试增强：** 后端添加详细日志，便于排查问题

🚀 **预期结果：** 用户登录后，所有需要认证的API都能正常访问，页面刷新也不受影响！
