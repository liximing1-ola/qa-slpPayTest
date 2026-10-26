# qa-slpPayTest 云服务器部署指南

## 1. 前置条件

云服务器需满足以下条件：

| 条件 | 要求 |
|------|------|
| 操作系统 | Linux (CentOS 7+ / Ubuntu 18.04+) |
| Python | 3.6 及以上 |
| Git | 任意版本 |
| 网络 | 可访问内网 192.168.1.x 网段 + 外网 |

---

## 2. 网络连通性检查

部署前请确认服务器可以连通以下地址：

| 目标地址 | 端口 | 用途 |
|---------|------|------|
| 192.168.1.23 | 443 | API 服务器（HTTPS） |
| 192.168.1.24 | 3306 | MySQL 数据库（主） |
| 192.168.1.24 | 6379 | Redis 缓存 |
| 192.168.11.46 | 3306 | MySQL 数据库（旧版） |
| hooks.slack.com | 443 | Slack 结果通知（需外网） |
| qyapi.weixin.qq.com | 443 | 企业微信通知（需外网） |

快速检查命令：

```bash
# 检查 API 服务器
curl -k https://192.168.1.23/ --connect-timeout 5

# 检查 MySQL
telnet 192.168.1.24 3306

# 检查 Redis
telnet 192.168.1.24 6379
```

---

## 3. 环境准备

### 安装 Python 和 Git

```bash
# CentOS / RHEL
yum install -y python3 python3-pip git gcc python3-devel

# Ubuntu / Debian
apt update
apt install -y python3 python3-pip git gcc python3-dev
```

### 验证安装

```bash
python3 --version   # 需要 3.6+
pip3 --version
git --version
```

---

## 4. 代码部署

### 方式一：手动部署

```bash
# 克隆代码
cd /home/ecs-user
git clone https://github.com/liximing1-ola/qa-slpPayTest.git
cd qa-slpPayTest

# 安装依赖
pip3 install -r requirements.txt

# 创建日志目录
mkdir -p log
```

### 方式二：一键部署

```bash
# 将项目上传到服务器后执行
bash deploy.sh
```

---

## 5. 配置确认

部署后请检查以下配置是否与服务器环境匹配：

### API 地址
- **文件**：`common/Config.py`
- **配置项**：`appInfo` 中的 `slp` 和 `xsg` 地址
- **当前值**：`https://192.168.1.23/`

### 数据库连接
- **文件**：`common/conSlpXsgMysql.py`
- **当前连接**：`192.168.1.24:3306`
- **用户名/密码**：`root` / `root`
- **数据库**：`xianshi`

### Redis 连接
- **文件**：`common/conRedis.py`
- **当前连接**：`192.168.1.24:6379`
- **无密码**

### 测试数据
- **文件**：`caseSlp/config.py`（SLP 测试数据和用户配置）
- **文件**：`caseXsg/config.py`（XSG 测试数据和用户配置）

> 如果服务器环境与上述配置不同，请修改对应文件中的配置项。

---

## 6. 执行测试

### 运行测试

```bash
# 执行 SLP（不夜星球）测试
python3 run_all_case.py slp

# 执行 XSG（小拾光）测试
python3 run_all_case.py xsg
```

### 运行指定测试文件

如需只运行某个测试文件，修改 `run_all_case.py` 第 75 行的 `pattern` 参数：

```python
# 运行单个文件（当前调试模式）
pattern = "test_gs_other_broker_slporder_room_new.py"

# 运行全部用例（正式模式）
pattern = "test_*.py"
```

### 测试执行流程

```
run_all_case.py
    ├── autoGitPull()        → 检查代码更新
    ├── Session.getSession() → 刷新用户 Token（调用测试接口）
    ├── unittest.discover()  → 发现并执行测试用例
    └── Robot.py             → 推送结果到 Slack / 企业微信
```

---

## 7. 定时任务（可选）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点执行 SLP 测试）
0 2 * * * cd /home/ecs-user/qa-slpPayTest && /usr/bin/python3 run_all_case.py slp >> log/cron.log 2>&1

# 查看已配置的定时任务
crontab -l
```

---

## 8. 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| pip install 报错 | 缺少编译工具 | 安装 `gcc python3-devel` |
| 数据库连接失败 | 网络不通 | 检查与 192.168.1.24 的连通性 |
| Token 获取失败 | 测试接口不可达 | 检查 192.168.1.23 的 /test/userToken 接口 |
| 通知发送失败 | Webhook 失效 | 检查 Robot.py 中的 Webhook URL |
| ModuleNotFoundError | 依赖未安装 | 重新执行 `pip3 install -r requirements.txt` |
| PermissionError | 日志目录不存在 | 执行 `mkdir -p log` |

---

## 9. 项目结构参考

```
qa-slpPayTest/
├── caseSlp/          # SLP 测试用例
├── caseXsg/          # XSG 测试用例
├── common/           # 公共模块（配置、数据库、Redis、请求等）
├── run_all_case.py   # 主入口脚本
├── requirements.txt  # Python 依赖
├── deploy.sh         # 一键部署脚本
└── DEPLOY.md         # 本文档
```
