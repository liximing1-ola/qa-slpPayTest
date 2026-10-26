# coding=utf-8
import ast
import os
import threading
import time
import traceback

import pymysql

from common.tools import get_last_weekday_timestamp


class _ClassProperty:
    """把类属性访问（conMysql.cur / conMysql.con）转发为动态调用"""

    def __init__(self, getter):
        self._getter = getter

    def __get__(self, instance, owner):
        return self._getter(owner)


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
            self._local.cur = self._local.con.cursor()
            return self._local.con
        try:
            self._local.con.ping(reconnect=True)
        except Exception:
            try:
                self._local.con.close()
            except Exception:
                pass
            self._local.con = self._open()
            self._local.cur = self._local.con.cursor()
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
        if accountType == 'bean':  # 查询用户账户扩展表金豆余额
            sql = "select money_coupon from xs_user_money_extend where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'cash':  # 查询用户账户扩展表 现金余额
            sql = "select cash from xs_user_money_extend where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'sum_money':  # 查询用户所有账户数据之和
            sql = "select money+money_b+money_cash_b+money_cash from xs_user_money where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'single_money':  # 查询用户单个账户数据
            sql = "select {} from xs_user_money where uid={}".format(money_type, uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if len(res) > 0:
                    return res[0]
                else:
                    return None
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'sum_commodity':  # 查询用户背包物品总数
            sql = 'select sum(num) from xs_user_commodity where uid ={}'.format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                return int(res[0])
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'num_commodity':  # 查询用户背包物品数量
            sql = "select num from xs_user_commodity where cid={} and uid={}".format(cid, uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'pay_room_money':  # 用户vip等级经验
            sql = "select pay_room_money from xs_user_profile where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'popularity':  # 用户人气等级经验
            sql = "select popularity from xs_user_popularity where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'id_commodity':  # 查询用户背包物品ID
            sql = "select id from xs_user_commodity where cid={} and uid={}".format(cid, uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if len(res) > 0:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'level':  # 查询用户爵位等级
            sql = "select level from xs_user_title_new where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if len(res) > 0:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'growth':  # 查询用户成长值
            sql = "select growth from xs_user_title_new where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if len(res) > 0:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'user_index':  # 查询用户salt
            sql = "select salt from xs_user_index where uid = {}".format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if len(res) > 0:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'relation_id':  # 查询用户守护关系id
            sql = "select id from xs_relation_defend where uid={} and defend_uid={} and relation_id={}". \
                format(payuid, uid, cid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    return 0
                if len(res) > 0:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'relation_config':  # 查询守护关系配置
            sql = "select id, name, money_value, break_money, upgrade_money from xs_relation_config where id={}".format(
                uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchall()
                column = [index[0] for index in conMysql.cur.description]
                data_dict = [dict(zip(column, row)) for row in res]
                return data_dict[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'union':
            sql = " select rid from xs_chatroom where property='{}' limit 1".format(accountType)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    raise EnvironmentError('库表无联盟房')
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        elif accountType == 'vip':
            sql = "select rid from xs_chatroom where property='{}' and app_id={} limit 1".format(accountType,app_id)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                if res is None:
                    raise EnvironmentError('库表无个人房')
                else:
                    return res[0]
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        # elif accountType == 'fleet':
        #     sql = " select rid from xs_chatroom where property='{}' limit 1".format(accountType)
        #     try:
        #         conMysql.cur.execute(sql)
        #         res = conMysql.cur.fetchone()
        #         if res is None:
        #             raise EnvironmentError('库表无家族房')
        #         else:
        #             if res[0] != config.bb_user['fleetRid']:
        #                 return res[0]
        #             return res[1]
        #     except Exception as error:
        #         print(error)
        elif accountType == 'pay_change':  # 查询用户消费记录数据
            sql = 'select reason from xs_pay_change where uid={} order by id desc LIMIT 1'.format(uid)
            try:
                conMysql.cur.execute(sql)
                res = conMysql.cur.fetchone()
                res_dict = ast.literal_eval(res[0])
                reason_value = '{}'.format(money_type)
                if reason_value in res_dict.keys():
                    return res_dict[reason_value]
                else:
                    return 0
            except Exception as error:
                print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        else:
            print('{} Error'.format(accountType))

    # 删除用户账户数据
    @staticmethod
    def deleteUserAccountSql(tableName, uid):
        if tableName == 'user_commodity':  # 清除用户背包数据
            sql = "delete from xs_user_commodity where uid={}".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('delete fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'user_title':  # 清除用户爵位数据
            sql = "delete from xs_user_title where uid = {} limit 5".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('delete fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        # elif tableName == 'user_profile':  # 修改用户profile爵位数据
        #     sql = "update xs_user_profile set title=0 where uid={} limit 1".format(uid)
        #     try:
        #         conMysql.cur.execute(sql)
        #     except Exception as error:
        #         conMysql.con.rollback()
        #         print('update fail', error)
        #     finally:
        #         conMysql.con.commit()
        elif tableName == 'pay_room_money':  # VIP 修改用户pay_room_money爵位数据
            sql = "update xs_user_profile set pay_room_money=0 where uid={} limit 1".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('update fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'broker_user':  # 删除用户工会记录
            sql = "delete from xs_broker_user where uid ={} limit 1".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('delete fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'chatroom':  # 删除用户商业房
            sql = "delete from xs_chatroom where uid ={} limit 1".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('delete fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'user_box':  # 清除xs_user_box用户数据
            sql = "delete from xs_user_box where uid={} limit 1".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('delete fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'user_title_new':  # xs_user_title_new每次跑都清一下subscribe_time，防止数据溢出
            sql = "update xs_user_title_new set subscribe_time=0 where uid={} limit 1".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('update fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'user_popularity':  # 人气值
            sql = "update xs_user_popularity set popularity=0 where uid ={};".format(uid)
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('update fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        elif tableName == 'pay_change':  # 送礼流水
            sql = f"delete from xs_pay_change WHERE uid = {uid};"
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('update fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        else:
            print('{} Error'.format(tableName))

    # 更新用户数据
    @staticmethod
    def updateUserInfoSql(tableName, uid, level=10):
        # if tableName == 'broker_user':  # 修改用户为打包结算主播
        #     sql = "update xs_broker_user set bid={}, uid={}, state=1, pack_cal=1 where id = 50 limit 1".format(bid, uid)
        #     try:
        #         conMysql.cur.execute(sql)
        #     except Exception as error:
        #         conMysql.con.rollback()
        #         print('update fail', error)
        #     finally:
        #         conMysql.con.commit()
        #
        # elif tableName == 'user_index':  # 修改用户xs_user_index:salt
        #     dateline = int(time.time())
        #     sql = "update xs_user_index set salt='{}', dateline={} where uid={} limit 1".format(bid, dateline, uid)
        #     try:
        #         conMysql.cur.execute(sql)
        #     except Exception as error:
        #         conMysql.con.rollback()
        #         print('update fail', error)
        #     finally:
        #         conMysql.con.commit()
        #
        # # elif tableName == 'chatroom':  # 修改用户为房间房主
        # #     sql = "update xs_chatroom set app_id=1, uid={}, settlement_channel='live', " \
        # #           "room_factory_type='business-soundchat' where rid={} limit 1".format(uid, bid)
        # #     try:
        # #         conMysql.cur.execute(sql)
        # #     except Exception as error:
        # #         conMysql.con.rollback()
        # #         print('update fail', error)
        # #     finally:
        # #         conMysql.con.commit()
        #
        # # elif tableName == 'super_chatroom':
        # #     sql = "update xs_chatroom set type='super-voice-fresh',property='business',version=737,room_factory_type='super-voice-fresh'," \
        # #           "room_module_id=73,settlement_channel='super-voice' where rid={}".format(uid)
        # #     try:
        # #         conMysql.cur.execute(sql)
        # #     except Exception as error:
        # #         conMysql.con.rollback()
        # #         print('update fail', error)
        # #     finally:
        # #         conMysql.con.commit()
        # # elif tableName == 'user_title_new':  #dev开通1个月贵族
        # #     sql = "update xs_user_title_new set subscribe_time={},growth=10,level=10 where uid={} limit 1".format(time.time()+30*60*60,uid)
        # #     try:
        # #         conMysql.cur.execute(sql)
        # #     except Exception as error:
        # #         conMysql.con.rollback()
        # #         print('update fail', error)
        # #     finally:
        # #         conMysql.con.commit()
        # # elif tableName == 'level':  # 查询用户爵位等级
        # #     sql = "update xs_user_title_new set level={} where uid={}".format(level,uid)
        # #     try:
        # #         conMysql.cur.execute(sql)
        # #     except Exception as error:
        # #         conMysql.con.rollback()
        # #         print('update fail', error)
        # #     finally:
        # #         conMysql.con.commit()
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
            subscribe_time = int(time.time()) + 1 * 24 * 60 * 60
            sql = f"""update xs_user_title_new set level={level},growth={jw_config[str(level)]},effective_value={jw_config[str(level)]},subscribe_time={subscribe_time},effective_time={subscribe_time} where uid ={uid};"""
            try:
                conMysql.cur.execute(sql)
            except Exception as error:
                conMysql.con.rollback()
                print('update fail:\n{}'.format(traceback.format_exc()))
            finally:
                conMysql.con.commit()
        else:
            print('{} Error'.format(tableName))

    # # 检查xs_gift配置
    # @staticmethod
    # def checkXsGiftConfig():
    #     sql = "update xs_gift set deleted=0 where id in {}".format(tuple(i for i in config.giftId.values()))
    #     try:
    #         conMysql.cur.execute(sql)
    #     except Exception as error:
    #         conMysql.con.rollback()
    #         print('update fail', error)
    #     finally:
    #         conMysql.con.commit()

    # 清空用户账户
    @staticmethod
    def updateUserMoneyClearSql(*uids):
        try:
            for uid in uids:
                sql = "update xs_user_money set money=0, money_b=0, money_cash=0, money_cash_b=0, gold_coin=0, " \
                      "money_debts=0 where uid={}".format(uid)
                conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 更新用户账户余额
    @staticmethod
    def updateMoneySql(uid, money=0, money_cash=0, money_cash_b=0, money_b=0, gold_coin=0, money_debts=0):
        sql = "update xs_user_money set money={}, money_b={}, money_cash={}, money_cash_b={},gold_coin={}, money_debts={} " \
              "where uid={} limit 1".format(money, money_b, money_cash, money_cash_b, gold_coin, money_debts, uid)
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # # 删除用户金豆账户数据
    # @staticmethod
    # def deleteUserBeanSql(*uids):
    #     try:
    #         for uid in uids:
    #             sql = "delete from xs_user_money_extend where uid = {} limit 1".format(uid)
    #             time.sleep(0.01)
    #             conMysql.cur.execute(sql)
    #             conMysql.con.commit()
    #     except Exception as error:
    #         conMysql.con.rollback()
    #         print('delete fail', error)

    # # 插入用户金豆余额
    # @staticmethod
    # def insertBeanSql(uid, money_coupon, cash=0, cash_lock=0):
    #     sql = "insert into xs_user_money_extend(uid, money_coupon, cash, cash_lock) values({},{},{},{})" \
    #         .format(uid, money_coupon, cash, cash_lock)
    #     try:
    #         conMysql.cur.execute(sql)
    #     except Exception as error:
    #         conMysql.con.rollback()
    #         print('insert fail', error)
    #     finally:
    #         time.sleep(0.01)
    #         conMysql.con.commit()
    #
    # # 更新箱子刷新物品
    # @staticmethod
    # def insertXsUserBox(uid, gift_cid=9, box_type='copper'):
    #     sql = "insert into xs_user_box (last_refresh_cid, last_refresh_sub_cid, uid, type) values ({},{},{},'{}')" \
    #         .format(gift_cid, gift_cid, uid, box_type)
    #     try:
    #         conMysql.cur.execute(sql)
    #     except Exception as error:
    #         conMysql.con.rollback()
    #         print('update fail', error)
    #     finally:
    #         conMysql.con.commit()

    # 用户背包增加测试数据
    @staticmethod
    def insertXsUserCommodity(uid, cid, num, state=0):
        conMysql.checkXsCommodity(cid)
        sql = "insert into xs_user_commodity (uid, cid, num, state) values ({}, {}, {}, {})".format(uid, cid, num,
                                                                                                    state)
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('insert fail', error)
        finally:
            conMysql.con.commit()

    @staticmethod
    def checkXsCommodity(cid, name='青铜体验券'):
        sql = "select name from xs_commodity where cid={}".format(cid)
        conMysql.cur.execute(sql)
        res = conMysql.cur.fetchone()
        if res is None:
            raise Exception('xs_commodity {}不存在'.format(name))

    # 查询工会是否存在
    @staticmethod
    def checkUserXsBroker(bid):
        sql = 'select * from xs_broker where bid={}'.format(bid)
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res is None:
                sql = "insert into xs_broker (bid,app_id,bname,creater,dateline,types) values({}, {}, '{}', {}, {}, '{}')" \
                    .format(bid, 1, '10086', bid, 1571481302, 'live')
                try:
                    conMysql.cur.execute(sql)
                except Exception as error:
                    conMysql.con.rollback()
                    print('insert fail', error)
            else:
                sql = 'update xs_broker set creater={} where bid={} limit 1'.format(bid, bid)
                try:
                    conMysql.cur.execute(sql)
                except Exception as error:
                    conMysql.con.rollback()
                    print('update fail:\n{}'.format(traceback.format_exc()))
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 查询用户是否是师父.不是就把他变成一代宗师（level=4，一代宗师）
    @staticmethod
    def checkUserXsMentorLevel(uid, level=4):
        sql = 'select * from xs_mentor_exp where uid={}'.format(uid)
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res is None:
                sql = 'insert into xs_mentor_exp (uid, level) values({}, {})'.format(uid, level)
                try:
                    conMysql.cur.execute(sql)
                except Exception as error:
                    conMysql.con.rollback()
                    print('insert fail', error)
            else:
                sql = "update xs_mentor_exp set level={} where uid={} limit 1".format(level, uid)
                try:
                    conMysql.cur.execute(sql)
                except Exception as error:
                    conMysql.con.rollback()
                    print('update fail:\n{}'.format(traceback.format_exc()))
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # # 查询工会用户
    # @staticmethod
    # def checkUserBroker(uid, bid=136594717):
    #     sql = 'select id from xs_broker_user where uid={}'.format(uid)
    #     try:
    #         conMysql.cur.execute(sql)
    #         res = conMysql.cur.fetchone()
    #         if res is None:
    #             sql = "insert into xs_broker_user(bid, uid, state) values ({}, {}, 1)".format(bid, uid)
    #             try:
    #                 conMysql.cur.execute(sql)
    #             except Exception as error:
    #                 conMysql.con.rollback()
    #                 print('insert fail', error)
    #         else:
    #             sql = 'update xs_broker_user set uid={}, bid={} where id={}'.format(uid, bid, res[0])
    #             try:
    #                 conMysql.cur.execute(sql)
    #             except Exception as error:
    #                 conMysql.con.rollback()
    #                 print('update fail:\n{}'.format(traceback.format_exc()))
    #     except Exception as error:
    #         print(error)
    #     finally:
    #         conMysql.con.commit()

    # # 查询用户分成比
    # @staticmethod
    # def checkBrokerUserRate(uid, creater, rate=100):
    #     sql = 'select * from config.bbc_broker_user_rate where uid={}'.format(uid)
    #     try:
    #         conMysql.cur.execute(sql)
    #         res = conMysql.cur.fetchone()
    #         if res is None:
    #             sql = 'insert into config.bbc_broker_user_rate (uid, broker_creater, rate) values({}, {}, {})' \
    #                 .format(uid, creater, rate)
    #             try:
    #                 conMysql.cur.execute(sql)
    #             except Exception as error:
    #                 conMysql.con.rollback()
    #                 print('insert fail', error)
    #         else:
    #             sql = "update config.bbc_broker_user_rate set rate={}, broker_creater={} where uid={} limit 1" \
    #                 .format(rate, creater, uid)
    #             try:
    #                 conMysql.cur.execute(sql)
    #             except Exception as error:
    #                 conMysql.con.rollback()
    #                 print('update fail:\n{}'.format(traceback.format_exc()))
    #     except Exception as error:
    #         print(error)
    #     finally:
    #         conMysql.con.commit()

    # 查询rid的房间类型
    @staticmethod
    def checkRidFactoryType(rid):
        sql = 'select room_factory_type from xs_chatroom where rid={}'.format(rid)
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if len(res) > 0:
                return res[0]
            else:
                return None
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    # 修改大神认证 1=同意,0=不同意
    @staticmethod
    def updateUserGodSql(uid, agreement_version):
        try:
            sql = f"update xs_user_settings set agreement_version={agreement_version} where uid={uid}"
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 查询甄选礼盒打赏数据
    @staticmethod
    def selectZxPayData(uid):
        sql = f"""
        SELECT JSON_EXTRACT(reason, '$.to') AS to_uid,JSON_EXTRACT(reason, '$.gid') AS gid,SUM(JSON_EXTRACT(reason, '$.num')) AS total_num FROM xs_pay_change WHERE uid = {uid} AND JSON_UNQUOTE(JSON_EXTRACT(reason, '$.obr')) IS NOT NULL GROUP BY gid, to_uid ORDER BY to_uid;
        """
        try:
            # 用 with 自动关闭游标，避免每次查询都泄漏一个游标对象
            with conMysql.con.cursor(cursor=pymysql.cursors.DictCursor) as cur:
                cur.execute(sql)
                res = cur.fetchall()
            if res is None:
                return 0
            else:
                return res
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    @staticmethod
    def checkUserBroker(uid):
        """校验是否是公会成员"""
        sql = f'select * from xs_broker_user where uid={uid} and deleted=0;'
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res:
                return True
            else:
                return False
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    @staticmethod
    def select_uid_rid():
        sql = """select uid,rid,room_factory_type from xs_chatroom where uid in (select uid from xs_user_mobile where mobile LIKE '%15008521%' or mobile like '%152%') and property='business';"""
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchall()
            print(res)
            return res
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    @staticmethod
    def selectGiftId():
        sql=f"""select a.id as gid,b.cid,a.name,a.price*100 from xs_gift as a left join xs_commodity as b on a.id=b.ext_id where b.cid is not null and b.type='gift';"""
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchall()
            print(res)
            return res
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    # 修改守护关系有效期
    @staticmethod
    def updateRelationExpire(uid1, uid2):
        expire_time = int(time.time()) + 30 * 24 * 60 * 60
        try:
            sql = f"""update xs_relation_defend set expire_time={expire_time},upgrade=0 where (uid={uid1} and defend_uid={uid2}) or (uid={uid2} and defend_uid={uid1}); """
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 删除用户账户数据
    @staticmethod
    def deleteXsUserAccelerationInfo(uid):
        sql = f"""delete from `xianshi`.`xs_user_acceleration_info` where uid={uid}"""
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('delete fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 添加并使用 vip/人气加速卡
    @staticmethod
    def insertXsUserAccelerationInfo(uid, speed=1.2):
        # 89386  1.2倍   89387  1.4倍
        try:
            expire_time = int(time.time()) + 30 * 24 * 60 * 60
            sql2 = f"""INSERT INTO `xianshi`.`xs_user_acceleration_info`(`id`, `uid`, `speed`, `expired_time`, `create_time`) VALUES (0, {uid}, {speed}, {expire_time}, 1736481872);"""
            conMysql.cur.execute(sql2)
        except Exception as error:
            conMysql.con.rollback()
            print('insert fail', error)
        finally:
            conMysql.con.commit()

    # 添加并使用 无损/有损优惠券
    @staticmethod
    def insertXsUserCouponUse(uid, cid=89370):
        # 89297 9折无损 有损
        # 89370 9折无损
        try:
            # 先删除再添加使用
            sql1 = f"""delete from `xianshi`.`xs_user_coupon_use` where uid={uid}"""
            conMysql.cur.execute(sql1)
            now_time = int(time.time())
            sql2 = f"""INSERT INTO `xianshi`.`xs_user_coupon_use`(`id`, `uid`, `coupon_type`, `cid`, `create_time`, `update_time`) VALUES (0, {uid}, 'pro_gift_discount', {cid}, {now_time}, {now_time});"""
            conMysql.cur.execute(sql2)
        except Exception as error:
            conMysql.con.rollback()
            print('insert fail', error)
        finally:
            conMysql.con.commit()

    # 更新房间 麦上用户信息
    @staticmethod
    def updateXsChatroomConfig(rid, uid=0, position=0):
        try:
            sql = f"""update xs_chatroom_config set uid={uid} where rid={rid} AND position = {position} limit 1;"""
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 删除冠歌信息
    @staticmethod
    def updateXsRoomUserMusicList(song_id):
        try:
            sql = f"""update xs_room_user_music_list set naming_id=0 where id={song_id};"""
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 修改冠歌信息-过期
    @staticmethod
    def updateXsRoomUserMusicNaming(song_id):
        try:
            sql = f"""update xs_room_user_music_naming set expire_time=expire_time-24*3600*365 where song_id={song_id} order by id desc limit 1;;"""
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('update fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 删除才艺厅购买观众位记录
    @staticmethod
    def deleteXsMicPermission(rid):
        sql = f"""delete from `xianshi`.`xs_mic_permission` where rid={rid}"""
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('delete fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    @staticmethod
    def checkUserAgreement(uid):
        """校验是否签署大神协议"""
        sql = f'select * from xs_user_settings where uid={uid} and agreement_version>=1;'
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res:
                return True
            else:
                return False
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    @staticmethod
    def checkUserWhite(uid,type_=198):
        """校验是否在人气标签白名单"""
        sql = f'select * from config.xsst_ktv_uid_white where uid={uid} and type={type_};'
        try:
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res:
                return True
            else:
                return False
        except Exception as error:
            print('SQL 执行异常:\n{}'.format(traceback.format_exc()))

    # 上周流水最高的厅 删除
    @staticmethod
    def deleteXsstRoomacsSum(uid):
        # 先删除
        sql = f"""delete from xsst.xsst_roomacs_sum where uid={uid};"""
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('delete fail:\n{}'.format(traceback.format_exc()))
        finally:
            conMysql.con.commit()

    # 上周流水最高的厅 插入
    @staticmethod
    def insertXsstRoomacsSum(uid, rid):
        date = get_last_weekday_timestamp()
        sql = f"""INSERT INTO `xsst`.`xsst_roomacs_sum`(`id`, `rid`, `uid`, `role`, `date`, `datetype`, `totaltime`, `totalnum`, `totalmic`, `totalmicnum`, `pay`, `income`, `totalpay`, `join_uid_datetype_date`) VALUES (0, {rid}, {uid}, 2, {date}, 1, 58379, 1, 0, 0, 0, 0, 0, '200255342-1-1772380800');"""
        try:
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('insert fail', error)
        finally:
            conMysql.con.commit()

if __name__ == '__main__':
    mysql = conMysql()
    data = mysql.updateUserInfoSql('user_title_new', '200000048', level=40)
    print(data)
