# coding=utf-8
import pymysql


class mysql:
    db_config = {"dev_46_db": '192.168.11.46',
                 "dev_46_user": 'root',
                 "dev_46_pas": '123456',
                 "ali_db": 'rm-bp1nfl3dp096d5o39.mysql.rds.aliyuncs.com',
                 "ali_user": 'super',
                 "ali_pas": 'dev123456'}
    _dbUrl = db_config['dev_46_db']
    _user = db_config['dev_46_user']
    _password = db_config['dev_46_pas']
    _dbName = 'xianshi'
    _dbPort = 3306

    @staticmethod
    def conMysql():
        con = pymysql.connect(host=mysql._dbUrl,
                              port=mysql._dbPort,
                              user=mysql._user,
                              passwd=mysql._password,
                              charset='utf8')
        con.select_db(mysql._dbName)
        cursor = con.cursor()
        return con, cursor

    # 更新用户的账户余额
    @staticmethod
    def updateMoneySql(uid, money=0, money_cash=0, money_cash_b=0, money_b=0, gold_coin=0):
        con, cur = mysql.conMysql()
        sql = "update xs_user_money set money={}, money_b={}, money_cash={}, money_cash_b={},gold_coin={} where uid={} limit 1" \
            .format(money, money_b, money_cash, money_cash_b, gold_coin, uid)
        try:
            cur.execute(sql)
        except Exception as error:
            con.rollback()
            print('update fail', error)
        finally:
            con.commit()

    # 查询用户当前所有账户余额之和
    @staticmethod
    def selectAllMoneySql(uid):
        con, cur = mysql.conMysql()
        sql = "select money+money_b+money_cash_b+money_cash from xs_user_money where uid={}".format(uid)
        try:
            cur.execute(sql)
            res = cur.fetchone()
            if len(res) > 0:
                return res[0]
            else:
                return None
        except Exception as error:
            print(error)

    # 清空用户背包
    @staticmethod
    def deleteUserCommoditySql(uid):
        con, cur = mysql.conMysql()
        sql = "delete from xs_user_commodity where uid={}".format(uid)
        try:
            cur.execute(sql)
        except Exception as error:
            con.rollback()
            print('delete fail', error)
        finally:
            con.commit()

    # 检查用户背包指定物品数量
    @staticmethod
    def checkUserCommoditySql(uid, cid):
        con, cur = mysql.conMysql()
        sql = "select num from xs_user_commodity where cid={} and uid={}".format(cid, uid)
        try:
            cur.execute(sql)
            res = cur.fetchone()
            if res is None:
                return 0
            else:
                return res[0]
        except Exception as error:
            print(error)

    # 检查用户背包所有物品数量
    @staticmethod
    def checkUserAllCommoditySql(uid):
        con, cur = mysql.conMysql()
        sql = 'select sum(num) from xs_user_commodity where uid ={}'.format(uid)
        try:
            cur.execute(sql)
            res = cur.fetchone()
            return int(res[0])
        except Exception as error:
            print(error)

    # 获得用户物品表的对应id
    @staticmethod
    def getUserCommodityIdSql(cid, uid):
        con, cur = mysql.conMysql()
        sql = "select id from xs_user_commodity where cid={} and uid={}".format(cid, uid)
        try:
            cur.execute(sql)
            res = cur.fetchone()
            if len(res) > 0:
                return res[0]
        except Exception as error:
            print(error)

    # 用户背包增加测试数据
    @staticmethod
    def insertXsUserCommodity(uid, cid, num, state=0):
        con, cur = mysql.conMysql()
        sql = "insert into xs_user_commodity (uid, cid, num, state) values ({}, {}, {}, {})".format(uid, cid, num,
                                                                                                    state)
        try:
            cur.execute(sql)
        except Exception as error:
            con.rollback()
            print('insert fail', error)
        finally:
            con.commit()

    #  生成一批uid
    @staticmethod
    def getUids(limit_num):
        con, cur = mysql.conMysql()
        sql = "select uid from xs_user_profile where uid>131542080 and app_id=1 limit {}".format(limit_num)
        uids = []
        try:
            cur.execute(sql)
            res = cur.fetchall()
            if res is None:
                print('error')
            else:
                for i in res:
                    uids.append(str(i[0]))
                print(tuple(uids))
                return tuple(uids)
        except Exception as error:
            print('fail', error)
        finally:
            con.commit()
