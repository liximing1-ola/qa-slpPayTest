#!/bin/bash
# ============================================
# qa-slpPayTest 云服务器一键部署脚本
# 使用方式：在云服务器上执行 bash deploy.sh
# ============================================

set -e

# ===== 配置区域（根据实际情况修改）=====
PROJECT_DIR="/home/ecs-user/qa-slpPayTest"
REPO_URL="https://github.com/liximing1-ola/qa-slpPayTest.git"
BRANCH="master"
# =======================================

echo "=========================================="
echo "  qa-slpPayTest 自动化部署脚本"
echo "=========================================="

echo ""
echo "[1/5] 检查 Python 环境..."
python3 --version || { echo "错误: 未安装 Python3，请先安装 python3"; exit 1; }
pip3 --version || { echo "错误: 未安装 pip3，请先安装 python3-pip"; exit 1; }

echo ""
echo "[2/5] 拉取/更新代码..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "项目已存在，执行 git pull..."
    cd "$PROJECT_DIR"
    git pull origin $BRANCH
else
    echo "克隆仓库到 $PROJECT_DIR ..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi
echo "当前版本: $(git log --oneline -1)"

echo ""
echo "[3/5] 安装 Python 依赖..."
pip3 install -r requirements.txt
echo "依赖安装完成"

echo ""
echo "[4/5] 创建必要目录..."
mkdir -p log
echo "目录准备完成"

echo ""
echo "[5/5] 执行测试..."
echo "请选择要执行的应用 [slp/xsg] (默认: slp):"
read app
app=${app:-slp}
echo "即将执行: python3 run_all_case.py $app"
python3 run_all_case.py $app

echo ""
echo "=========================================="
echo "  部署执行完成！"
echo "=========================================="
