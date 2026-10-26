****Common类的设计****

`Request.py` 封装request方法，可以支持多协议扩展（get\post\put）

`Logs.py` 封装记录log方法，分为：debug、info、warning、error、critical

`Session.py` 封装获取登录token方法

`conSlpXsgMysql.py` 封装 MySQL 操作（每线程独立连接、断线自动重连）

`conRedis.py` 封装 Redis 操作

`tools.py` 用例公共工具（数据准备、背包礼物、加速卡、token 等），SLP/XSG 共用一份实现；
`caseSlp/tools.py`、`caseXsg/tools.py` 仅做转发，保持用例里原有的 import 写法不变

`config.py` 常用数据路径

`Consts` 全局数据记录

`runFailed.py` 失败重试方法（只重试断言失败，跳过 skip）

`report.py` 执行结果汇总：收集每条用例的 des，执行结束后在控制台与 `log/notPassCase.log` 里完整罗列未通过用例（编号/状态/用例名/des/失败明细）

****环境变量（都可选，不设置则用默认值）****

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ASSERT_SLEEP` | `0.3` | 每次状态码断言前的等待秒数（rpc 延迟补偿），设 `0` 关闭 |
| `REQUEST_INTERVAL` | `2` | 同一账号两次请求的最小间隔秒数（服务端频控） |
| `FREQUENT_RETRY` | `2` | 命中「请勿频繁操作」后的重试次数 |
| `LIST_PASS` | `0` | 推送时额外逐条列出通过用例（仅 `PUSH_WX=1` 时生效） |
| `PUSH_WX` | `0` | 是否推送到企业微信群；默认关闭，结果只输出到控制台与 `log/notPassCase.log` |
| `WX_BOT_SLP` | 内置测试群 | 企微群机器人 webhook，换群/轮换 key 不用改代码 |
| `SLACK_BOT_SLP` | 内置 webhook | slack 通知地址（`to='slack'` 时使用） |
| `DB_HOST` / `DB_USER` / `DB_PASS` | `192.168.1.24` / `root` / `root` | 测试库连接信息 |

****用例编写规则（unittest）****

测试文件以test_开头（以_test结尾也可以）

测试类以Test开头，并且不能带有 init 方法

测试函数以test_开头

****case目录****

整理项目相关用例

pip3 install gitpython
