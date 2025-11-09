#!/bin/bash

# VBRPG Demo 启动脚本
# 用于启动前后端服务进行演示

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   VBRPG 演示环境启动脚本              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# 检查环境配置
check_env() {
    echo -e "${YELLOW}1. 检查环境配置...${NC}"
    
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        echo -e "${RED}❌ 后端 .env 文件不存在${NC}"
        echo -e "${YELLOW}提示: 请复制 backend/.env.example 到 backend/.env 并配置${NC}"
        exit 1
    fi
    
    if [ ! -f "$FRONTEND_DIR/.env" ]; then
        echo -e "${YELLOW}⚠️  前端 .env 文件不存在，正在创建...${NC}"
        cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
        echo -e "${GREEN}✓ 已创建前端 .env 文件${NC}"
    fi
    
    echo -e "${GREEN}✓ 环境配置检查完成${NC}"
    echo ""
}

# 初始化数据库
init_database() {
    echo -e "${YELLOW}2. 初始化数据库...${NC}"
    cd "$BACKEND_DIR"
    
    # 创建数据目录
    mkdir -p data
    
    # 运行数据库迁移
    if [ ! -f "data/vbrpg.db" ]; then
        echo -e "${BLUE}→ 运行数据库迁移...${NC}"
        uv run alembic upgrade head
        echo -e "${GREEN}✓ 数据库迁移完成${NC}"
        
        # 添加种子数据（需要在 backend 目录运行）
        echo -e "${BLUE}→ 添加演示数据...${NC}"
        cd "$BACKEND_DIR" && uv run python -m scripts.seed_data
        echo -e "${GREEN}✓ 演示数据添加完成${NC}"
    else
        echo -e "${GREEN}✓ 数据库已存在${NC}"
    fi
    
    echo ""
}

# 安装依赖
install_deps() {
    echo -e "${YELLOW}3. 检查并安装依赖...${NC}"
    
    # 后端依赖
    cd "$BACKEND_DIR"
    if [ ! -d ".venv" ]; then
        echo -e "${BLUE}→ 安装后端依赖...${NC}"
        uv sync
        echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
    else
        echo -e "${GREEN}✓ 后端依赖已安装${NC}"
    fi
    
    # 前端依赖
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo -e "${BLUE}→ 安装前端依赖...${NC}"
        npm install
        echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
    else
        echo -e "${GREEN}✓ 前端依赖已安装${NC}"
    fi
    
    echo ""
}

# 启动服务
start_services() {
    echo -e "${YELLOW}4. 启动服务...${NC}"
    echo ""
    
    # 启动后端（确保在 backend 目录）
    echo -e "${BLUE}→ 启动后端服务 (端口 8000)...${NC}"
    cd "$BACKEND_DIR"
    uv run uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/.backend.log" 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
    
    # 等待后端启动
    sleep 3
    
    # 启动前端
    echo -e "${BLUE}→ 启动前端服务 (端口 5173)...${NC}"
    cd "$FRONTEND_DIR"
    npm run dev > "$PROJECT_ROOT/.frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   🎉 服务启动成功！                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📍 访问地址:${NC}"
    echo -e "   前端: ${GREEN}http://localhost:5173${NC}"
    echo -e "   后端 API: ${GREEN}http://localhost:8000${NC}"
    echo -e "   API 文档: ${GREEN}http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}💡 提示:${NC}"
    echo -e "   - 按 ${RED}Ctrl+C${NC} 停止所有服务"
    echo -e "   - 查看后端日志: tail -f $PROJECT_ROOT/.backend.log"
    echo -e "   - 查看前端日志: tail -f $PROJECT_ROOT/.frontend.log"
    echo ""
    
    # 保存 PID 到文件
    echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid"
    echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid"
    
    # 等待进程
    wait
}

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    
    if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
        BACKEND_PID=$(cat "$PROJECT_ROOT/.backend.pid")
        kill $BACKEND_PID 2>/dev/null || true
        rm "$PROJECT_ROOT/.backend.pid"
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
    fi
    
    if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
        FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend.pid")
        kill $FRONTEND_PID 2>/dev/null || true
        rm "$PROJECT_ROOT/.frontend.pid"
        echo -e "${GREEN}✓ 前端服务已停止${NC}"
    fi
    
    echo -e "${BLUE}再见！${NC}"
    exit 0
}

# 捕获 Ctrl+C
trap cleanup INT TERM

# 主流程
main() {
    check_env
    install_deps
    init_database
    start_services
}

main
