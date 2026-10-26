# qa-slpPayTest 云服务器部署指南

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码仓库地址 | `https://github.com/liximing1-ola/qa-slpPayTest.git` |
| 服务器部署路径 | `/home/ecs-user/qa-slpPayTest` |
| Python 版本要求 | 3.9+（当前服务器 3.11） |
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
python3 --version   # 需要 3.9+
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

优先用环境变量，不改代码：

| 环境变量 | 默认值 | 用途 |
|---------|--------|------|
| `DB_HOST` / `DB_USER` / `DB_PASS` | `192.168.1.24` / `root` / `root` | MySQL 连接 |
| `WX_BOT_SLP` | 内置测试群 webhook | 企微通知（换群/轮换 key） |
| `ASSERT_SLEEP` | `0.3` | 断言前等待秒数，设 `0` 可提速 |
| `REQUEST_INTERVAL` | `2` | 同账号请求最小间隔（频控） |
| `PUSH_WX` | `0` | 是否推送到企业微信群，默认为关闭 |
| `LIST_PASS` | `0` | 推送时列出通过用例（需 `PUSH_WX=1`） |

```bash
export DB_HOST=192.168.1.24
export WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx'
```

| 配置文件 | 配置项 | 当前值 |
|---------|--------|--------|
| `common/Config.py` | API 地址 | `https://192.168.1.23/` |
| `common/conRedis.py` | Redis | `192.168.1.24:6379`，无密码 |

---

## 注意事项

1. **测试用例范围**：`run_all_case.py` 的 `all_case()` 里 `pattern` 现为 `test_*.py`（全量），只调试单个文件时把这一行改成对应文件名
2. **查看执行结果**：执行结束会在控制台输出带编号的完整未通过清单（编号 / FAIL|ERROR|SKIP / 用例名 / des / 失败明细），
   同时写入 `log/notPassCase.log`；失败与异常的完整堆栈只写 `log/failCase.log`，不在控制台刷屏。
   云服务器上可直接：
   ```bash
   tail -n 100 log/notPassCase.log   # 未通过清单（先看这个）
   tail -n 200 log/failCase.log      # 需要看堆栈时
   ```
   企业微信推送默认关闭，需要推送时：`PUSH_WX=1 python3 run_crontab_case.py slp`
3. **定时任务**（可选）：
   ```bash
   crontab -e
   # 每天凌晨 2 点执行
   0 2 * * * cd /home/ecs-user/qa-slpPayTest && python3 run_all_case.py slp >> log/cron.log 2>&1
   ```
4. **退出码**：`run_all_case.py` / `run_crontab_case.py` 执行结束后会按结果返回退出码，
   可直接被 cron 告警、调度平台或 `cmd && 下一步` 识别：

   | 退出码 | 含义 |
   |--------|------|
   | `0` | 全部用例通过 |
   | `1` | 存在失败或异常（跳过不计） |
   | `2` | 命令行参数错误（如 `run_crontab_case.py slpp`） |

   ```bash
   # 失败时让 cron 发邮件 / 触发告警（MAILTO 生效的前提就是非 0 退出码）
   0 2 * * * cd /home/ecs-user/qa-slpPayTest && python3 run_all_case.py slp >> log/cron.log 2>&1
   ```

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| pip install 报错 | 先确认 `python3 --version` ≥ 3.9；`requirements.txt` 已精简为 requests / urllib3 / PyMySQL / redis 四个实际依赖 |
| 数据库连接失败 | 检查服务器与 `192.168.1.24` 的网络连通性 |
| Token 获取失败 | 检查 `192.168.1.23` 的 `/test/userToken` 接口是否可访问 |
| ModuleNotFoundError | 重新执行 `pip3 install -r requirements.txt` |
