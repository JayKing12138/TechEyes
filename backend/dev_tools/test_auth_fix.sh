#!/bin/bash
# 测试认证和项目权限隔离

echo "=========================================="
echo "测试认证和项目权限修复"
echo "=========================================="
echo ""

API_BASE="http://localhost:8000/api"

# 测试1: 未登录访问项目列表
echo "📌 测试1: 未登录访问项目列表（应该返回401）"
response=$(curl -s -w "\n%{http_code}" "$API_BASE/projects")
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "401" ]; then
    echo "✅ 正确返回401未授权"
else
    echo "❌ 错误：状态码 $status_code"
fi
echo ""

# 测试2: 登录用户A
echo "📌 测试2: 登录用户（获取token）"
login_response=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')

token=$(echo "$login_response" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -n "$token" ]; then
    echo "✅ 登录成功，token: ${token:0:20}..."
else
    echo "❌ 登录失败"
    echo "响应: $login_response"
    exit 1
fi
echo ""

# 测试3: 使用token访问项目列表
echo "📌 测试3: 使用token访问项目列表（应该返回200）"
response=$(curl -s -w "\n%{http_code}" "$API_BASE/projects" \
  -H "Authorization: Bearer $token")
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" = "200" ]; then
    echo "✅ 成功访问项目列表"
    echo "返回数据: $body" | head -c 200
    echo "..."
else
    echo "❌ 错误：状态码 $status_code"
    echo "响应: $body"
fi
echo ""

# 测试4: 创建项目
echo "📌 测试4: 创建测试项目"
create_response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/projects" \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试项目'$(date +%s)'", "description": "自动化测试项目"}')
status_code=$(echo "$create_response" | tail -n1)
body=$(echo "$create_response" | head -n -1)

if [ "$status_code" = "201" ]; then
    echo "✅ 项目创建成功"
    project_id=$(echo "$body" | grep -o '"id":[0-9]*' | head -1 | sed 's/"id"://')
    echo "项目ID: $project_id"
else
    echo "❌ 错误：状态码 $status_code"
    echo "响应: $body"
fi
echo ""

# 测试5: token过期后访问
echo "📌 测试5: 无效token访问（应该返回401）"
response=$(curl -s -w "\n%{http_code}" "$API_BASE/projects" \
  -H "Authorization: Bearer invalid_token_12345")
status_code=$(echo "$response" | tail -n1)

if [ "$status_code" = "401" ]; then
    echo "✅ 正确拒绝无效token"
else
    echo "❌ 错误：状态码 $status_code"
fi
echo ""

echo "=========================================="
echo "测试完成！"
echo "=========================================="
