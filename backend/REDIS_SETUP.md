# Redis 安装与启动指南

## 安装 Redis (macOS)

### 方法1: 使用 Homebrew (推荐)
```bash
# 安装 Redis
brew install redis

# 查看安装信息
brew info redis
```

### 方法2: 使用 Docker
```bash
# 拉取 Redis 镜像
docker pull redis:latest

# 运行 Redis 容器
docker run -d -p 6379:6379 --name redis-cache redis:latest
```

## 启动 Redis

### Homebrew 方式

#### 前台启动 (调试用)
```bash
redis-server
```
按 `Ctrl+C` 停止

#### 后台服务启动 (推荐)
```bash
# 启动 Redis 服务
brew services start redis

# 查看服务状态
brew services list

# 停止 Redis 服务
brew services stop redis

# 重启 Redis 服务
brew services restart redis
```

### Docker 方式
```bash
# 启动容器
docker start redis-cache

# 停止容器
docker stop redis-cache

# 查看日志
docker logs redis-cache
```

## 验证 Redis 是否正常运行

### 方法1: 使用 redis-cli
```bash
# 连接到 Redis
redis-cli

# 在 Redis CLI 中测试
127.0.0.1:6379> ping
PONG

127.0.0.1:6379> set test "hello"
OK

127.0.0.1:6379> get test
"hello"

127.0.0.1:6379> exit
```

### 方法2: 使用 Python 测试
```bash
# 在 techeyes 环境中测试
conda activate techeyes
python -c "import redis; r=redis.from_url('redis://localhost:6379'); print('Redis连接成功:', r.ping())"
```

## 配置说明

### 默认配置
- **端口**: 6379
- **地址**: localhost (127.0.0.1)
- **密码**: 无 (本地开发)

### 修改配置（如需要）
```bash
# 查找 Redis 配置文件
brew info redis | grep redis.conf

# 编辑配置文件
vim /opt/homebrew/etc/redis.conf

# 修改后重启
brew services restart redis
```

## 常见问题

### 端口被占用
```bash
# 检查谁在使用 6379 端口
lsof -i:6379

# 杀死进程
kill -9 <PID>
```

### Redis 启动失败
```bash
# 查看日志
tail -f /opt/homebrew/var/log/redis.log
```

## 对话缓存系统的影响

### Redis 可用时
- **L1缓存**: 内存缓存 (180秒有效期)
- **L2缓存**: Redis缓存 (24小时有效期) ✅
- **L3缓存**: SQLite语义缓存 (永久，相似度匹配)

### Redis 不可用时
- **L1缓存**: 内存缓存 (180秒有效期)
- **L2缓存**: 自动禁用 (优雅降级)
- **L3缓存**: SQLite语义缓存 (永久，相似度匹配)

> **注意**: 即使不启动Redis，对话功能仍正常工作，只是会跳过L2缓存层。

## 性能对比

| 场景 | 无Redis | 有Redis |
|------|---------|---------|
| 单进程重复查询 | L1命中 | L1命中 |
| 进程重启后查询 | L3语义搜索(慢) | L2直接命中(快) |
| 跨用户相同查询 | L3语义搜索 | L2可能命中 |

**建议**: 开发阶段可不启动，生产环境建议启动Redis提升性能。
