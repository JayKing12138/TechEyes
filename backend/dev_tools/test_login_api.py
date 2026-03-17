"""测试登录后的API请求"""

import requests
import json

# 测试用户 crq (ID: 2)
username = 'crq'
password = 'your_password'  # 你需要提供正确的密码

print(f"测试用户: {username}")
print()

# 1. 登录获取token
print("1. 尝试登录...")
login_response = requests.post('http://localhost:8000/api/auth/login', json={
    'username': username,
    'password': password
})

if login_response.status_code != 200:
    print(f"❌ 登录失败: {login_response.status_code}")
    print(login_response.text)
    print("\n请提供正确的密码，或者使用前端登录后查看浏览器控制台")
    exit(1)

login_data = login_response.json()
token = login_data['access_token']
user_id = login_data['user']['id']
print(f"✅ 登录成功！用户ID: {user_id}")
print(f"Token: {token[:30]}...")

# 2. 使用token获取会话列表
print("\n2. 获取会话列表...")
headers = {
    'Authorization': f'Bearer {token}',
    'X-Client-Id': 'test-client-123'
}

conversations_response = requests.get(
    'http://localhost:8000/api/chat/conversations?limit=10',
    headers=headers
)

print(f"状态码: {conversations_response.status_code}")
data = conversations_response.json()
print(f"会话数量: {data['total']}")
print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

# 3. 检查响应头
print("\n3. 检查响应头...")
print(f"X-Token-Expired: {conversations_response.headers.get('X-Token-Expired', '未设置')}")
