#!/bin/bash

# Phase 7 测试运行脚本
# 运行所有Phase 7相关的测试

set -e

echo "=================================="
echo "Phase 7 功能测试"
echo "=================================="
echo ""

cd "$(dirname "$0")/../frontend"

echo "📦 检查依赖..."
if ! command -v npm &> /dev/null; then
    echo "❌ npm未安装，请先安装Node.js"
    exit 1
fi

echo "✅ npm已安装"
echo ""

echo "📥 安装测试依赖..."
npm install --silent
echo "✅ 依赖安装完成"
echo ""

echo "=================================="
echo "运行单元测试"
echo "=================================="
echo ""

echo "🧪 测试1: 动画图标组件"
npm run test tests/unit/icons/AnimatedIcons.spec.js -- --reporter=verbose
echo ""

echo "🧪 测试2: 图片优化工具"
npm run test tests/unit/utils/imageOptimization.spec.js -- --reporter=verbose
echo ""

echo "🧪 测试3: 资源配置"
npm run test tests/unit/config/assetConfig.spec.js -- --reporter=verbose
echo ""

echo "🧪 测试4: 图标集成"
npm run test tests/unit/icons/IconIntegration.spec.js -- --reporter=verbose
echo ""

echo "=================================="
echo "生成覆盖率报告"
echo "=================================="
echo ""

npm run test:coverage -- tests/unit/icons tests/unit/utils tests/unit/config
echo ""

echo "✅ 所有测试完成！"
echo ""
echo "📊 覆盖率报告已生成在: frontend/coverage/index.html"
echo "💡 使用浏览器打开查看详细报告"
echo ""
echo "运行完整测试套件: npm run test"
echo "监听模式: npm run test:watch"
echo "UI模式: npm run test:ui"
