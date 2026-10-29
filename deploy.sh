#!/bin/bash
# ============================================
# qa-slpPayTest 云服务器一键部署脚本
# 使用方式：bash deploy.sh
# ============================================

set -e

# ===== 配置区域（按实际环境用环境变量覆盖，不写进仓库）=====
# 项目目录默认取脚本所在目录，换位置就设 PROJECT_DIR
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
# 只有首次 clone 才需要仓库地址，用 REPO_URL=<地址> bash deploy.sh 传入
REPO_URL="${REPO_URL:-}"
# 服务器跟踪的功能分支，master 只是快照
BRANCH="${BRANCH:-lxm}"
# ===================================================

echo "=========================================="
echo "  qa-slpPayTest 自动化部署脚本"
echo "=========================================="

echo ""
echo "[1/4] 检查 Python 环境..."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || { echo "错误: 需要 Python 3.9+，当前版本 $(python3 --version 2>&1)"; exit 1; }
pip3 --version || { echo "错误: 未安装 pip3"; exit 1; }

echo ""
echo "[2/4] 拉取/更新代码..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git pull origin $BRANCH
else
    [ -n "$REPO_URL" ] || {
        echo "错误: 目录不存在且未设置 REPO_URL，无法克隆"
        echo "用法: REPO_URL=<仓库地址> bash deploy.sh"
        exit 1
    }
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi
echo "当前版本: $(git log --oneline -1)"

echo ""
echo "[3/4] 安装 Python 依赖..."
pip3 install -r requirements.txt

echo ""
echo "[4/4] 创建必要目录..."
mkdir -p log

echo ""
echo "执行测试..."
echo "请选择要执行的应用 [slp/xsg] (默认: slp):"
read app
app=${app:-slp}
# run_all_case.py 在有失败/异常时返回 1；这里刻意不中断部署流程（set -e 仍对上面各步生效），
# 否则“部署成功但测试有失败”会被误判成部署失败
python3 run_all_case.py "$app" || echo "注意: 本轮测试存在失败/异常（退出码 $?），详见上方输出与 log/notPassCase.log"

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
