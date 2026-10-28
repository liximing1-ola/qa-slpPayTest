# qa-slpPayTest 云服务器部署指南

## 基本信息

| 项目 | 值 |
|------|-----|
| 代码仓库地址 | `<仓库地址>` |
| 服务器部署路径 | `/home/<user>/qa-slpPayTest` |
| Python 版本要求 | 3.9+（当前服务器 3.11） |
| 测试应用 | SLP / XSG |

> 本文所有地址、路径、账号均为占位符（`<api-host>` / `<db-host>` / `<user>` 等），
> 真实环境信息只配在 `common/Config.py` 与环境变量里，不写进文档。

---

## 快速开始（3 步完成部署）

### 第 1 步：登录服务器，拉取代码

```bash
cd /home/<user>
git clone <仓库地址>
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
cd /home/<user>/qa-slpPayTest
git pull origin master
pip3 install -r requirements.txt    # 依赖有变更时执行
```

---

## 网络要求

服务器必须能访问以下地址：

| 地址 | 端口 | 用途 |
|------|------|------|
| `<api-host>` | 443 | API 服务器 |
| `<db-host>` | 3306 | MySQL 数据库 |
| `<db-host>` | 6379 | Redis |
| `<legacy-db-host>` | 3306 | MySQL（旧版） |
| `hooks.slack.com` | 443 | 结果通知（需外网） |
| `qyapi.weixin.qq.com` | 443 | 企业微信通知（需外网） |

---

## 需要修改的配置（如果服务器环境不同）

优先用环境变量，不改代码：

| 环境变量 | 默认值 | 用途 |
|---------|--------|------|
| `DB_HOST` / `DB_USER` / `DB_PASS` | 见 `common/Config.py` | MySQL 连接 |
| `WX_BOT_SLP` | 见 `common/Config.py` | 企微通知（换群/轮换 key） |
| `ASSERT_SLEEP` | `0.3` | 断言前等待秒数，设 `0` 可提速 |
| `REQUEST_INTERVAL` | `2` | 同账号请求最小间隔（频控） |
| `PUSH_WX` | `0` | 是否推送到企业微信群，默认为关闭 |
| `LIST_PASS` | `0` | 推送时列出通过用例（需 `PUSH_WX=1`） |

```bash
export DB_HOST=<db-host>
export WX_BOT_SLP='https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<key>'
```

| 配置文件 | 配置项 | 填什么 |
|---------|--------|--------|
| `common/Config.py` | API 地址 | `https://<api-host>/` |
| `common/conRedis.py` | Redis | `<db-host>:6379`，无密码 |

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
3. **定时任务**：

   先确认 python3 的绝对路径——cron 的 PATH 很精简，只写 `python3` 在 cron 里经常找不到：

   ```bash
   which python3      # 例如 /usr/bin/python3
   crontab -e
   ```

   ```cron
   # 每天 03:00 拉最新代码后跑全量；日志按日期落盘，同时清理 30 天前的
   0 3 * * * cd /home/<user>/qa-slpPayTest && mkdir -p log && { find log -name 'cron_*.log' -mtime +30 -delete; git pull -q --ff-only; /usr/bin/python3 run_crontab_case.py slp; } >> log/cron_$(date +\%F).log 2>&1
   ```

   几处不是随手写的：

   - **用 `run_crontab_case.py` 不用 `run_all_case.py`**：前者专为定时任务，不逐条播报通过用例，只打汇总 + 未通过清单；137 条全量下来后者几千行，日志没法看
   - **每天先 `git pull --ff-only`**：不拉的话定时任务跑的永远是部署那天的代码，改过的用例根本不会生效。`--ff-only` 避免在服务器上产生合并提交；用 `;` 不用 `&&`，pull 失败也继续用现有代码跑，不把整条链断掉
   - **日志按日期分文件**：`cron.log` 会无限增长，`$(date +\%F)` 一天一个（cron 里 `%` 必须转义成 `\%`）
   - **清理日志要放在最前面**：`{ }` 的退出码取块内最后一条命令，把 `find` 放在末尾会把 python 的退出码盖掉，cron 就永远收不到失败信号（MAILTO / 调度平台告警全失效）
   - **`find ... -mtime +30 -delete`**：只删 30 天前的，不会动当天正在写的文件
   - **`mkdir -p log` 必须在重定向之前**：`>> log/cron_x.log` 是 shell 在开始执行前打开的文件，目录不存在就直接报错，整条命令连 python 都不会起动
   - **时间选凌晨**：全量约 5 分钟、会造数扣费，避开有人手工测试的时段
   - **服务器上不要手工改代码**：`git pull --ff-only` 遇到本地修改会直接拒绝，日志里会一直报 pull 失败，而用例跑的还是旧代码

   需要同时推企业微信群：把命令里的 `run_crontab_case.py` 前面加上 `PUSH_WX=1 `。

4. **看结果、追趋势**：

   ```bash
   tail -30 log/cron_$(date +%F).log                    # 当天结果
   grep -h '重试后才通过' log/cron_*.log | sort | uniq -c   # 每天一行，这就是趋势
   ```

   第二行值得每天看一眼：`重试后才通过: N 条（X%）` 统计的是「被 @Retry 兜住、但确实失败过一次」的请求。
   当前它稳定指向 naming_song 的「房间类型错误」（服务端约 8% 拒绝，证据见 README 排查手册第 4 条），
   服务端修好后这行会变成「无」。全量口径只有 0.7%（分母 137，而这个文件只跑一轮），
   想看清这个 bug 就单跑它（分子分母都是 10 条，信噪比高 14 倍）：

   ```bash
   CASE=test_naming_song python3 run_all_case.py slp 2>&1 | grep '重试后才通过'
   ```

5. **退出码**：`run_all_case.py` / `run_crontab_case.py` 执行结束后会按结果返回退出码，
   可直接被 cron 告警、调度平台或 `cmd && 下一步` 识别：

   | 退出码 | 含义 |
   |--------|------|
   | `0` | 全部用例通过 |
   | `1` | 存在失败或异常（跳过不计） |
   | `2` | 命令行参数错误（如 `run_crontab_case.py slpp`） |

   **注意：被 `@Retry` 救回来的用例不算失败，退出码仍是 0。** 只靠退出码会漏掉「稳定存在但被重试掩盖」的问题，
   必须配合上面那行重试率一起看。失败时让 cron 发邮件：在 crontab 顶部加 `MAILTO="你的邮箱"`（前提就是非 0 退出码）。

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| pip install 报错 | 先确认 `python3 --version` ≥ 3.9；`requirements.txt` 已精简为 requests / urllib3 / PyMySQL / redis 四个实际依赖 |
| 数据库连接失败 | 检查服务器与 `<db-host>` 的网络连通性 |
| Token 获取失败 | 检查 `<api-host>` 的 `/test/userToken` 接口是否可访问 |
| ModuleNotFoundError | 重新执行 `pip3 install -r requirements.txt` |
