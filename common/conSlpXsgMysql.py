# coding=utf-8
import ast
import os
import re
import threading
import time

import pymysql

from common import Request
from common.tools import get_last_weekday_timestamp

# 写库语句的起始关键字：先剥掉前导注释再判首 token，避免 "-- 清数据\nupdate ..." 这类写法漏判
_WRITE_KEYWORDS = ('insert', 'update', 'delete', 'replace', 'truncate', 'alter', 'drop', 'create', 'set', 'call')
_LEADING_COMMENT_RE = re.compile(r'^(?:\s*(?:--[^\n]*(?:\n|$)|#[^\n]*(?:\n|$)|/\*.*?\*/))*\s*', re.S)
_WRITE_RE = re.compile(r'^\s*(?:' + '|'.join(_WRITE_KEYWORDS) + r')\b', re.I)


def _is_write_sql(sql):
    """语句是否会写库（兼容前导空白/注释、全大写写法）"""
    return bool(_WRITE_RE.match(_LEADING_COMMENT_RE.sub('', str(sql))))


def _safe_rollback():
    """回滚只是尽力而为。

    连接已经断开时 rollback 自己会抛错，若不加保护，它会把后面的 DbQueryError 抢掉，
    SQL 与真实失败原因全部丢失——而这正是最需要看清故障的时候。
    """
    try:
        conMysql.con.rollback()
    except Exception as error:
        # 留痕但不影响主流程：连接断开时的回滚失败本身就是重要现场信息
        print('[DB] rollback 失败（忽略）: {}'.format(error))


class DbQueryError(Exception):
    """数据库访问失败。

    以前数据层把异常 print 掉后隐式返回 None，使"库里没这条数据"和"SQL 根本执行失败"
    （连接断开/列名错/表不存在）无法区分，用例最终只报"实际结果: None"，
    真正的基础设施故障被伪装成断言失败。这里统一抛出，交给用例框架记为 ERROR。
    """


# ===== SQL 执行模板 =====
# 全文件曾有 40+ 处逐字相同的 try/execute/except/fetch 样板，只有 SQL 字符串和异常文案不同，
# 加一个查询就要复制八行。收成下面几个函数后，各处只留自己的 SQL 和取值语义。
def _query_one(sql):
    """执行查询并取第一行；SQL 故障统一抛 DbQueryError。返回 None 表示没有数据"""
    try:
        conMysql.cur.execute(sql)
        return conMysql.cur.fetchone()
    except Exception as error:
        raise DbQueryError('SQL 执行异常, SQL: {}, 原因: {}'.format(sql, error)) from error


def _query_all(sql):
    """执行查询并取全部行；SQL 故障统一抛 DbQueryError"""
    try:
        conMysql.cur.execute(sql)
        return conMysql.cur.fetchall()
    except Exception as error:
        raise DbQueryError('SQL 执行异常, SQL: {}, 原因: {}'.format(sql, error)) from error


def _query_all_dict(sql):
    """用字典游标查询，返回 [{列名: 值}]；游标用 with 自动关闭"""
    try:
        with conMysql.con.cursor(cursor=pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()
    except Exception as error:
        raise DbQueryError('SQL 执行异常, SQL: {}, 原因: {}'.format(sql, error)) from error


def _query_dict_row(sql):
    """查询并把第一行转成 {列名: 值}

    SQL 故障与「查不到数据」都抛 DbQueryError，但文案分开写：以前空结果也报
    "SQL 执行异常"，排查时会误以为是连接或语法问题，实际只是配置行不存在。
    """
    try:
        conMysql.cur.execute(sql)
        rows = conMysql.cur.fetchall()
        column = [index[0] for index in conMysql.cur.description]
        result = [dict(zip(column, row)) for row in rows]
    except Exception as error:
        raise DbQueryError('SQL 执行异常, SQL: {}, 原因: {}'.format(sql, error)) from error
    if not result:
        raise DbQueryError('查询结果为空, SQL: {}'.format(sql))
    return result[0]


def _exec_write(sql, action):
    """执行写 SQL：失败先回滚再抛 DbQueryError，成功失败都 commit

    commit 放 finally 是历史行为（失败路径等于“回滚后再提交一次空事务”），
    调用方依赖“每次调用后连接上不残留未提交事务”，这里原样保留。
    """
    try:
        conMysql.cur.execute(sql)
    except Exception as error:
        _safe_rollback()
        raise DbQueryError('{}, SQL: {}, 原因: {}'.format(action, sql, error)) from error
    finally:
        conMysql.con.commit()


def _exec_writes(sqls, action):
    """按顺序执行多条写 SQL，任一条失败即整体回滚并抛 DbQueryError（报出失败的那条）

    连接是 autocommit=True，若逐条直接 execute 就等于每条各自提交：第二条失败时
    第一条已经落地。典型受害场景是「先删旧券、再插新券」（insertXsUserCouponUse），
    插入失败会留下「券被删掉了」的中间态，后续用例全部拿不到券、连锁报错。
    这里显式开事务，让多条语句要么全成功、要么全不发生。
    """
    current = '<begin>'
    try:
        # autocommit 连接上调 begin() 才会真正开启事务，之后的 execute 不再逐条提交
        conMysql.con.begin()
        for current in sqls:
            conMysql.cur.execute(current)
    except Exception as error:
        _safe_rollback()
        raise DbQueryError('{}, SQL: {}, 原因: {}'.format(action, current, error)) from error
    conMysql.con.commit()


class _ClassProperty:
    """把类属性访问（conMysql.cur / conMysql.con）转发为动态调用"""

    def __init__(self, getter):
        self._getter = getter

    def __get__(self, instance, owner):
        return self._getter(owner)


class _ReplayCursor:
    """重试轮次只放行查询的游标代理。

    用例失败重跑时，用例体开头的数据准备会把余额/背包重置掉，而下单请求已经回放（不重复下单），
    若同时放行写库，就变成"状态被清零 + 订单没产生"，重试必然第二次失败。
    这里直接丢弃写语句，让重试轮只重做读断言——正是结算延迟这类抖动需要的。
    """

    def __init__(self, real_cursor):
        self._real = real_cursor

    def execute(self, sql, *args, **kwargs):
        if Request.is_replaying() and _is_write_sql(sql):
            print('[重试] 跳过写库: {}'.format(str(sql).strip()[:100]))
            return 0
        return self._real.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        if Request.is_replaying() and _is_write_sql(sql):
            print('[重试] 跳过写库: {}'.format(str(sql).strip()[:100]))
            return 0
        return self._real.executemany(sql, *args, **kwargs)

    def __enter__(self):
        # with 走的是特殊方法而不是 __getattr__，不显式补上就会在回放态下直接 TypeError
        self._real.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._real.__exit__(exc_type, exc, tb)

    def __getattr__(self, item):
        # fetchone / fetchall / rowcount / description 等全部透传给真实游标
        return getattr(self._real, item)


class _ThreadLocalConnection:
    """
    按线程（gevent 下为 greenlet）隔离的 MySQL 连接。

    历史实现把 con/cur 定义成类属性全局共享：
    1. 所有用例、所有线程共用同一个游标，并发时 A 的查询结果会被 B 覆盖；
    2. 只在 import 时 ping 一次，MySQL 连接超时后所有查询都会失败且异常被 print 吞掉。
    这里改为每线程独立连接 + 取用前 ping 自动重连，对上层保持 con/cur 的原有用法。
    """

    def __init__(self, connect_kwargs, db_name):
        self._connect_kwargs = connect_kwargs
        self._db_name = db_name
        self._local = threading.local()

    def _open(self):
        con = pymysql.connect(**self._connect_kwargs)
        con.select_db(self._db_name)
        return con

    def connection(self):
        """返回当前线程的连接，连接失效时自动重建"""
        if getattr(self._local, 'con', None) is None:
            self._local.con = self._open()
            # 换连接必须同步换游标，否则会拿着已失效的游标继续查询
            self._local.cur = _ReplayCursor(self._local.con.cursor())
            return self._local.con
        try:
            self._local.con.ping(reconnect=True)
        except Exception:
            try:
                self._local.con.close()
            except Exception:
                pass
            self._local.con = self._open()
            self._local.cur = _ReplayCursor(self._local.con.cursor())
        return self._local.con

    def cursor(self):
        self.connection()
        return self._local.cur

    def commit(self):
        self.connection().commit()

    def rollback(self):
        self.connection().rollback()

    def close(self):
        con = getattr(self._local, 'con', None)
        if con is not None:
            try:
                con.close()
            finally:
                self._local.con = None
                self._local.cur = None


# 清理用户数据：表名 -> (SQL 模板, 动作)。SQL 只用 {uid} 占位，动作只用于异常文案。
# 以前每个表一个 if/elif 分支，9 个分支套着同一份 8 行 try/except/finally，加一张表要复制
# 一遍样板；改成表驱动后新增表只需在这里添一行
_ACCOUNT_CLEANUP_SQL = {
    'user_commodity': ('delete from xs_user_commodity where uid={uid}', '数据删除'),
    'user_title': ('delete from xs_user_title where uid = {uid} limit 5', '数据删除'),
    'pay_room_money': ('update xs_user_profile set pay_room_money=0 where uid={uid} limit 1', '数据更新'),
    'broker_user': ('delete from xs_broker_user where uid ={uid} limit 1', '数据删除'),
    'chatroom': ('delete from xs_chatroom where uid ={uid} limit 1', '数据删除'),
    'user_box': ('delete from xs_user_box where uid={uid} limit 1', '数据删除'),
    'user_title_new': ('update xs_user_title_new set subscribe_time=0 where uid={uid} limit 1', '数据更新'),
    'user_popularity': ('update xs_user_popularity set popularity=0 where uid ={uid};', '数据更新'),
    'pay_change': ('delete from xs_pay_change WHERE uid = {uid};', '数据删除'),
}


class conMysql:
    db_config = {
        # 测试库连接信息可用环境变量覆盖（DB_HOST / DB_USER / DB_PASS），换环境无需改代码
        # "ali_db": '127.0.0.1',
        "ali_db": os.environ.get('DB_HOST') or '192.168.1.24',
        "ali_user": os.environ.get('DB_USER') or 'root',
        "ali_pas": os.environ.get('DB_PASS') or 'root'
    }
    _dbUrl = db_config['ali_db']
    _user = db_config['ali_user']
    _password = db_config['ali_pas']
    _dbName = 'xianshi'
    _dbPort = 3306
    # 连接改为首次使用时才建立，避免 import 阶段就去连数据库
    _db = _ThreadLocalConnection(
        {
            'host': _dbUrl,
            'port': _dbPort,
            'user': _user,
            'passwd': _password,
            'charset': 'utf8',
            'autocommit': True,
        },
        _dbName,
    )
    con = _ClassProperty(lambda cls: cls._db.connection())
    cur = _ClassProperty(lambda cls: cls._db.cursor())


    # 查询用户账户信息
    @staticmethod
    def selectUserInfoSql(accountType, uid="200254463", money_type='money_cash_b', cid=263, payuid="200254777", app_id=66):
        """查询用户账户信息（重试轮会复用首轮下单前的读值）

        回放轮不再真正下单，库里的"下单前基线"已经是首轮结算后的值。用例里大量存在
        old = 查 → 下单 → 断言 new == old + 增量 的写法，若不还原 old，断言必然失败；
        "插入后取 id"这类准备产物同理，不沿用首轮结果就拿不到 id。
        因此按"同一查询在本轮的调用序号"对齐，只回放首轮下单之前的读值，
        下单之后的读值仍真实查询——那正是重试要观察的目标。
        """
        # salt 不随订单变化，且它处于"取 token"的路径上：回放轮命中响应后不会再取 token，
        # 这种少一次的调用会让同 key 的序号错位，直接不纳入回放
        if accountType == 'user_index':
            return conMysql._query_user_info(accountType, uid, money_type, cid, payuid, app_id)

        key = (accountType, uid, money_type, cid, payuid, app_id)
        seq = Request.next_read_index(key)
        if Request.is_replaying():
            cached = Request.replay_read(key, seq)
            if cached is not Request.READ_MISS:
                print('[重试] 复用下单前读数: {}, uid={}'.format(accountType, uid))
                return cached
        value = conMysql._query_user_info(accountType, uid, money_type, cid, payuid, app_id)
        Request.remember_read(key, seq, value)
        return value

    @staticmethod
    def _query_user_info(accountType, uid, money_type, cid, payuid, app_id):
        """实际执行某个 accountType 对应的查询，失败抛 DbQueryError"""
        if accountType == 'bean':  # 查询用户账户扩展表金豆余额
            row = _query_one("select money_coupon from xs_user_money_extend where uid={}".format(uid))
            return 0 if row is None else row[0]
        elif accountType == 'cash':  # 查询用户账户扩展表 现金余额
            row = _query_one("select cash from xs_user_money_extend where uid={}".format(uid))
            return 0 if row is None else row[0]
        elif accountType == 'sum_money':  # 查询用户所有账户数据之和
            row = _query_one("select money+money_b+money_cash_b+money_cash from xs_user_money where uid={}".format(uid))
            return 0 if row is None else row[0]
        elif accountType == 'single_money':  # 查询用户单个账户数据
            row = _query_one("select {} from xs_user_money where uid={}".format(money_type, uid))
            return None if row is None else row[0]
        elif accountType == 'sum_commodity':  # 查询用户背包物品总数
            row = _query_one('select sum(num) from xs_user_commodity where uid ={}'.format(uid))
            # 没有背包数据时 sum() 返回 NULL，属于合法空结果，不能当成 SQL 异常
            if row is None or row[0] is None:
                return 0
            return int(row[0])
        elif accountType == 'num_commodity':  # 查询用户背包物品数量
            row = _query_one("select num from xs_user_commodity where cid={} and uid={}".format(cid, uid))
            return 0 if row is None else row[0]
        elif accountType == 'pay_room_money':  # 用户vip等级经验
            row = _query_one("select pay_room_money from xs_user_profile where uid={}".format(uid))
            return 0 if row is None else row[0]
        elif accountType == 'popularity':  # 用户人气等级经验
            row = _query_one("select popularity from xs_user_popularity where uid={}".format(uid))
            return 0 if row is None else row[0]
        elif accountType == 'id_commodity':  # 查询用户背包物品ID
            row = _query_one("select id from xs_user_commodity where cid={} and uid={}".format(cid, uid))
            return None if row is None else row[0]
        elif accountType == 'level':  # 查询用户爵位等级
            row = _query_one("select level from xs_user_title_new where uid={}".format(uid))
            return None if row is None else row[0]
        elif accountType == 'growth':  # 查询用户成长值
            row = _query_one("select growth from xs_user_title_new where uid={}".format(uid))
            return None if row is None else row[0]
        elif accountType == 'user_index':  # 查询用户salt
            row = _query_one("select salt from xs_user_index where uid = {}".format(uid))
            return None if row is None else row[0]
        elif accountType == 'relation_id':  # 查询用户守护关系id
            row = _query_one("select id from xs_relation_defend where uid={} and defend_uid={} and relation_id={}"
                             .format(payuid, uid, cid))
            return 0 if row is None else row[0]
        elif accountType == 'relation_config':  # 查询守护关系配置
            return _query_dict_row("select id, name, money_value, break_money, upgrade_money "
                                   "from xs_relation_config where id={}".format(uid))
        elif accountType == 'union':
            row = _query_one("select rid from xs_chatroom where property='{}' limit 1".format(accountType))
            if row is None:
                # 这是环境的房间数据缺失，不是 SQL 故障，单独抛出便于区分
                raise EnvironmentError('库表无联盟房')
            return row[0]
        elif accountType == 'vip':
            row = _query_one("select rid from xs_chatroom where property='{}' and app_id={} limit 1"
                             .format(accountType, app_id))
            if row is None:
                raise EnvironmentError('库表无个人房')
            return row[0]
        elif accountType == 'pay_change':  # 查询用户消费记录数据
            sql = 'select reason from xs_pay_change where uid={} order by id desc LIMIT 1'.format(uid)
            row = _query_one(sql)
            # 没有消费记录属于合法空结果
            if row is None:
                return 0
            try:
                reason_dict = ast.literal_eval(row[0])
            except Exception as error:
                raise DbQueryError('SQL 执行异常, SQL: {}, 原因: {}'.format(sql, error)) from error
            return reason_dict.get('{}'.format(money_type), 0)
        else:
            raise ValueError('未知的查询类型: {}, 可选值见 selectUserInfoSql 的 if 分支'.format(accountType))

    # 执行任意只读 SQL（表名/字段调用方事先不确定时用）
    @staticmethod
    def selectRawDict(sql):
        """返回 [{列名: 值}]

        给「失败现场快照」这类通用场景用：要查什么表取决于用例当轮实际请求了哪些账号，
        没法在 selectUserInfoSql 里逐个枚举。只读，不参与业务断言。
        """
        return _query_all_dict(sql)

    # 删除用户账户数据
    @staticmethod
    def deleteUserAccountSql(tableName, uid):
        """按表名清理用户数据，表名与 SQL 的对应关系见 _ACCOUNT_CLEANUP_SQL

        未知表名保持原有行为：打一行日志、不做任何操作（调用方传错名字时不应该抛错，
        因为不少用例把它当“尽力清理”在用）。
        """
        item = _ACCOUNT_CLEANUP_SQL.get(tableName)
        if item is None:
            print('{} Error'.format(tableName))
            return
        sql = item[0].format(uid=uid)
        _exec_write(sql, item[1] + '失败')

    # 更新用户数据
    @staticmethod
    def updateUserInfoSql(tableName, uid, level=10, growth=None):
        """修改用户爵位等级

        :param growth: 贵族成长值。None 表示按 SLP 的爵位成长值表换算；
            XSG 的爵位体系与 SLP 完全不同（殿=2500 万，SLP 同 level 的亲王只有 650 万），
            跨 App 用例必须显式传入本 App 的成长值，否则库里 level 与 growth 不自洽，
            服务端按 growth 换算爵位时会算出与用例预期不同的倍率。
        """
        if tableName == 'user_title_new':  # 修改用户爵位等级
            jw_config = {
                "0": 0,
                "10": 0,
                "20": 20000,
                "30": 80000,
                "40": 250000,
                "50": 1000000,
                "60": 2500000,
                "70": 6500000,
                "80": 15000000,
                "90": 50000000,
            }
            if growth is None:
                growth = jw_config[str(level)]
            subscribe_time = int(time.time()) + 1 * 24 * 60 * 60
            sql = f"""update xs_user_title_new set level={level},growth={growth},effective_value={growth},subscribe_time={subscribe_time},effective_time={subscribe_time} where uid ={uid};"""
            _exec_write(sql, '数据更新失败')
        else:
            print('{} Error'.format(tableName))


    # 清空用户账户
    @staticmethod
    def updateUserMoneyClearSql(*uids):
        _exec_writes(["update xs_user_money set money=0, money_b=0, money_cash=0, money_cash_b=0, gold_coin=0, "
                      "money_debts=0 where uid={}".format(uid) for uid in uids], '数据更新失败')

    # 更新用户账户余额
    @staticmethod
    def updateMoneySql(uid, money=0, money_cash=0, money_cash_b=0, money_b=0, gold_coin=0, money_debts=0):
        sql = "update xs_user_money set money={}, money_b={}, money_cash={}, money_cash_b={},gold_coin={}, money_debts={} " \
              "where uid={} limit 1".format(money, money_b, money_cash, money_cash_b, gold_coin, money_debts, uid)
        _exec_write(sql, '数据更新失败')



    # 用户背包增加测试数据
    @staticmethod
    def insertXsUserCommodity(uid, cid, num, state=0):
        conMysql.checkXsCommodity(cid)
        sql = "insert into xs_user_commodity (uid, cid, num, state) values ({}, {}, {}, {})".format(uid, cid, num,
                                                                                                    state)
        _exec_write(sql, '数据插入失败')

    @staticmethod
    def checkXsCommodity(cid, name='青铜体验券'):
        # 走 _query_one 而不是裸 execute：连库失败时要抛 DbQueryError，
        # 而不是把 pymysql 的原始异常糊到调用栈里
        if _query_one("select name from xs_commodity where cid={}".format(cid)) is None:
            raise Exception('xs_commodity {}不存在'.format(name))

    # 查询工会是否存在
    @staticmethod
    def checkUserXsBroker(bid):
        if _query_one('select * from xs_broker where bid={}'.format(bid)) is None:
            _exec_write("insert into xs_broker (bid,app_id,bname,creater,dateline,types) values({}, {}, '{}', {}, {}, '{}')"
                        .format(bid, 1, '10086', bid, 1571481302, 'live'), '数据插入失败')
        else:
            _exec_write('update xs_broker set creater={} where bid={} limit 1'.format(bid, bid), '数据更新失败')

    # 查询用户是否是师父.不是就把他变成一代宗师（level=4，一代宗师）
    @staticmethod
    def checkUserXsMentorLevel(uid, level=4):
        if _query_one('select * from xs_mentor_exp where uid={}'.format(uid)) is None:
            _exec_write('insert into xs_mentor_exp (uid, level) values({}, {})'.format(uid, level), '数据插入失败')
        else:
            _exec_write("update xs_mentor_exp set level={} where uid={} limit 1".format(level, uid), '数据更新失败')


    # 查询rid的房间类型
    @staticmethod
    def checkRidFactoryType(rid):
        row = _query_one('select room_factory_type from xs_chatroom where rid={}'.format(rid))
        return None if row is None else row[0]

    # 房间现场：行数/类型/删除标记/房主。排查「房间类型错误」时用
    @staticmethod
    def checkRoomScene(rid):
        """房间在库里的全部行（同一个 rid 可能有多行，所以返回列表）

        「房间类型错误」这句文案既可能是房间数据真的坏了，也可能是服务端 RPC/回源失败
        复用了同一句话。只看一句文案分不开，必须同时看：行数是否唯一、deleted 是否被置 1、
        room_factory_type 是否还是期望值。
        """
        rows = _query_all('select uid, room_factory_type, deleted from xs_chatroom where rid={}'.format(rid))
        return {
            'rows': len(rows),
            'factory_type': [row[1] for row in rows],
            'deleted': [row[2] for row in rows],
            'owner': [row[0] for row in rows],
        }

    # 修改大神认证 1=同意,0=不同意
    @staticmethod
    def updateUserGodSql(uid, agreement_version):
        _exec_write(f"update xs_user_settings set agreement_version={agreement_version} where uid={uid}", '数据更新失败')

    # 查询甄选礼盒打赏数据
    @staticmethod
    def selectZxPayData(uid):
        sql = f"""
        SELECT JSON_EXTRACT(reason, '$.to') AS to_uid,JSON_EXTRACT(reason, '$.gid') AS gid,SUM(JSON_EXTRACT(reason, '$.num')) AS total_num FROM xs_pay_change WHERE uid = {uid} AND JSON_UNQUOTE(JSON_EXTRACT(reason, '$.obr')) IS NOT NULL GROUP BY gid, to_uid ORDER BY to_uid;
        """
        res = _query_all_dict(sql)
        # 没有打赏记录时是空的查询结果（pymysql 的 fetchall 返回空 tuple，可迭代），
        # 不能退回 0：调用方直接 for 遍历，0 会抛 TypeError
        return res

    @staticmethod
    def checkUserBroker(uid):
        """校验是否是公会成员"""
        return bool(_query_one(f'select * from xs_broker_user where uid={uid} and deleted=0;'))

    @staticmethod
    def select_uid_rid():
        sql = """select uid,rid,room_factory_type from xs_chatroom where uid in (select uid from xs_user_mobile where mobile LIKE '%15008521%' or mobile like '%152%') and property='business';"""
        res = _query_all(sql)
        print(res)
        return res

    @staticmethod
    def selectGiftId():
        sql=f"""select a.id as gid,b.cid,a.name,a.price*100 from xs_gift as a left join xs_commodity as b on a.id=b.ext_id where b.cid is not null and b.type='gift';"""
        res = _query_all(sql)
        print(res)
        return res

    # 修改守护关系有效期
    @staticmethod
    def updateRelationExpire(uid1, uid2):
        expire_time = int(time.time()) + 30 * 24 * 60 * 60
        sql = f"""update xs_relation_defend set expire_time={expire_time},upgrade=0 where (uid={uid1} and defend_uid={uid2}) or (uid={uid2} and defend_uid={uid1}); """
        _exec_write(sql, '数据更新失败')

    # 删除用户账户数据
    @staticmethod
    def deleteXsUserAccelerationInfo(uid):
        sql = f"""delete from `xianshi`.`xs_user_acceleration_info` where uid={uid}"""
        _exec_write(sql, '数据删除失败')

    # 添加并使用 vip/人气加速卡
    @staticmethod
    def insertXsUserAccelerationInfo(uid, speed=1.2):
        # 89386  1.2倍   89387  1.4倍
        expire_time = int(time.time()) + 30 * 24 * 60 * 60
        sql = f"""INSERT INTO `xianshi`.`xs_user_acceleration_info`(`id`, `uid`, `speed`, `expired_time`, `create_time`) VALUES (0, {uid}, {speed}, {expire_time}, 1736481872);"""
        _exec_write(sql, '数据插入失败')

    # 添加并使用 无损/有损优惠券
    @staticmethod
    def insertXsUserCouponUse(uid, cid=89370):
        # 89297 9折无损 有损
        # 89370 9折无损
        now_time = int(time.time())
        # 先删除再添加使用
        sql1 = f"""delete from `xianshi`.`xs_user_coupon_use` where uid={uid}"""
        sql2 = f"""INSERT INTO `xianshi`.`xs_user_coupon_use`(`id`, `uid`, `coupon_type`, `cid`, `create_time`, `update_time`) VALUES (0, {uid}, 'pro_gift_discount', {cid}, {now_time}, {now_time});"""
        _exec_writes([sql1, sql2], '数据写入失败')

    # 更新房间 麦上用户信息
    @staticmethod
    def updateXsChatroomConfig(rid, uid=0, position=0):
        sql = f"""update xs_chatroom_config set uid={uid} where rid={rid} AND position = {position} limit 1;"""
        _exec_write(sql, '数据更新失败')

    # 删除冠歌信息
    @staticmethod
    def updateXsRoomUserMusicList(song_id):
        sql = f"""update xs_room_user_music_list set naming_id=0 where id={song_id};"""
        _exec_write(sql, '数据更新失败')

    # 修改冠歌信息-过期
    @staticmethod
    def updateXsRoomUserMusicNaming(song_id):
        # 结尾原来多打了一个分号（limit 1;;），多余的分号在 COM_QUERY 下会变成语法错误
        sql = f"""update xs_room_user_music_naming set expire_time=expire_time-24*3600*365 where song_id={song_id} order by id desc limit 1;"""
        _exec_write(sql, '数据更新失败')

    # 删除才艺厅购买观众位记录
    @staticmethod
    def deleteXsMicPermission(rid):
        _exec_write(f"""delete from `xianshi`.`xs_mic_permission` where rid={rid}""", '数据删除失败')

    @staticmethod
    def checkUserAgreement(uid):
        """校验是否签署大神协议"""
        return bool(_query_one(f'select * from xs_user_settings where uid={uid} and agreement_version>=1;'))

    @staticmethod
    def checkUserWhite(uid,type_=198):
        """校验是否在人气标签白名单"""
        return bool(_query_one(f'select * from config.xsst_ktv_uid_white where uid={uid} and type={type_};'))

    # 上周流水最高的厅 删除
    @staticmethod
    def deleteXsstRoomacsSum(uid):
        # 先删除
        _exec_write(f"""delete from xsst.xsst_roomacs_sum where uid={uid};""", '数据删除失败')

    # 上周流水最高的厅 插入
    @staticmethod
    def insertXsstRoomacsSum(uid, rid):
        # 取上周中间（周四 0 点）而不是窗口起点（周一 0 点）：服务端 buyeLastWeekRange()
        # 按自己的时区算 [上周一 00:00, 本周一 00:00)，date 若恰好等于起点，
        # 任何时区偏差（比如 RPC 机跑 UTC）或边界比较差异都会让它掉出窗口，
        # 放到周中后即使偏差一两天也仍在区间内
        date = get_last_weekday_timestamp() + 3 * 86400
        # join_uid_datetype_date 是 uid-1-date 的拼接值，原来写死成 '200255342-1-1772380800'
        # （uid 是别人、1772380800 是 2026-03-02 造数据时的那一周），和本次插入的 uid/date
        # 完全对不上。服务端若按这个字段（或它上的唯一索引）定位上周厅，就永远查不到，
        # 所有跳档分成用例都会掉进“上周厅不存在”的兜底比例（实测 0.6 / 0.2）
        join_key = '{}-1-{}'.format(uid, date)
        sql = f"""INSERT INTO `xsst`.`xsst_roomacs_sum`(`id`, `rid`, `uid`, `role`, `date`, `datetype`, `totaltime`, `totalnum`, `totalmic`, `totalmicnum`, `pay`, `income`, `totalpay`, `join_uid_datetype_date`) VALUES (0, {rid}, {uid}, 2, {date}, 1, 58379, 1, 0, 0, 0, 0, 0, '{join_key}');"""
        _exec_write(sql, '数据插入失败')

if __name__ == '__main__':
    mysql = conMysql()
    data = mysql.updateUserInfoSql('user_title_new', '200000048', level=40)
    print(data)
