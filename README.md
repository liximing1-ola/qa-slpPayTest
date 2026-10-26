****Common类的设计****

`Request.py` 封装request方法，可以支持多协议扩展（get\post\put）

`paramsYaml.py` 读取Conf内各种配置文件，包括：不同环境的配置

`Logs.py` 封装记录log方法，分为：debug、info、warning、error、critical

`Session.py` 封装获取登录token方法

`conSlpXsgMysql.py` 封装 MySQL 操作（每线程独立连接、断线自动重连）

`Basic.yml` 存放yaml文件

`config.py` 常用数据路径

`Consts` 全局数据记录

`HTMLTestRunner` 生成html方法

`runFailed.py` 失败重试方法

****用例编写规则（unittest）****

测试文件以test_开头（以_test结尾也可以）

测试类以Test开头，并且不能带有 init 方法

测试函数以test_开头

****case目录****

整理项目相关用例

pip3 install gitpython


