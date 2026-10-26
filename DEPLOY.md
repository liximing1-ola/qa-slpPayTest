# qa-slpPayTest 云服务器部署指南

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码仓库地址 | `https://github.com/liximing1-ola/qa-slpPayTest.git` |
| 服务器部署路径 | `/home/ecs-user/qa-slpPayTest` |
| Python 版本要求 | 3.6+ |
| 测试应用 | SLP（不夜星球）/ XSG（小拾光） |

---

## 快速开始（3 步完成部署）

### 第 1 步：登录服务器，拉取代码

```bash
cd /home/ecs-user
git clone https://github.com/liximing1-ola/qa-slpPayTest.git
cd qa-slpPayTest
```

### 第 2 步：安装依赖

```bash
pip3 install -r requirements.txt
mkdir -p log
```

### 第 3 步：执行测试

```bash
# 执行 SLP 测试
python3 run_all_case.py slp

# 执行 XSG 测试
python3 run_all_case.py xsg
```

---

## 服务器环境准备（首次部署需执行）

```bash
# CentOS / RHEL
yum install -y python3 python3-pip git gcc python3-devel

# Ubuntu / Debian
apt update && apt install -y python3 python3-pip git gcc python3-dev
```

验证：
```bash
python3 --version   # 需要 3.6+
pip3 --version
git --version
```

---

## 后续更新代码

```bash
cd /home/ecs-user/qa-slpPayTest
git pull origin master
pip3 install -r requirements.txt    # 依赖有变更时执行
```

---

## 网络要求

服务器必须能访问以下地址：

| 地址 | 端口 | 用途 |
|------|------|------|
| 192.168.1.23 | 443 | API 服务器 |
| 192.168.1.24 | 3306 | MySQL 数据库 |
| 192.168.1.24 | 6379 | Redis |
| 192.168.11.46 | 3306 | MySQL（旧版） |
| hooks.slack.com | 443 | 结果通知（需外网） |
| qyapi.weixin.qq.com | 443 | 企业微信通知（需外网） |

---

## 需要修改的配置（如果服务器环境不同）

| 配置文件 | 配置项 | 当前值 |
|---------|--------|--------|
| `common/Config.py` | API 地址 | `https://192.168.1.23/` |
| `common/conSlpXsgMysql.py` | MySQL | `192.168.1.24:3306`，用户 `root`，密码 `root`，库 `xianshi` |
| `common/conRedis.py` | Redis | `192.168.1.24:6379`，无密码 |

---

## 注意事项

1. **测试用例范围**：`run_all_case.py` 第 75 行 `pattern` 当前为单文件调试模式，运行全部用例需改为 `test_*.py`
2. **定时任务**（可选）：
   ```bash
   crontab -e
   # 每天凌晨 2 点执行
   0 2 * * * cd /home/ecs-user/qa-slpPayTest && python3 run_all_case.py slp >> log/cron.log 2>&1
   ```

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| pip install 报错 | 安装编译工具：`yum install gcc python3-devel` 或 `apt install gcc python3-dev` |
| 数据库连接失败 | 检查服务器与 `192.168.1.24` 的网络连通性 |
| Token 获取失败 | 检查 `192.168.1.23` 的 `/test/userToken` 接口是否可访问 |
| ModuleNotFoundError | 重新执行 `pip3 install -r requirements.txt` |
