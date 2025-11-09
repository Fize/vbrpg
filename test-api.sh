#!/bin/bash

# 测试后端 API 功能

echo "🔍 测试后端 API"
echo "=================="
echo ""

# 1. 健康检查
echo "1️⃣ 健康检查:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# 2. 获取房间列表
echo "2️⃣ 获取房间列表:"
curl -s http://localhost:8000/api/v1/rooms | python3 -m json.tool
echo ""

echo "✅ 测试完成！现在可以在浏览器中测试创建房间功能"
echo "   访问: http://localhost:5173"
