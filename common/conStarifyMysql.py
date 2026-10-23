# coding=utf-8
import time
import pymysql


class conMysql:
    db_config = {
        "ali_db": '127.0.0.1',
        "ali_user": 'root',
        "ali_pas": 'root'
    }
    _dbUrl = db_config['ali_db']
    _user = db_config['ali_user']
    _password = db_config['ali_pas']
    _dbName = 'xianshi'
    _dbPort = 3306
    con = pymysql.connect(host=_dbUrl,
                          port=_dbPort,
                          user=_user,
                          passwd=_password,
                          charset='utf8',
                          autocommit=True)
    con.select_db(_dbName)
    con.ping(reconnect=True)
    cur = con.cursor()

    @staticmethod
    def sql_fetchone(sql):
        try:
            # print(sql)
            conMysql.cur.execute(sql)
            res = conMysql.cur.fetchone()
            if res is None:
                return 0
            elif res[0] is None:
                return 0
            else:
                return res[0]
        except Exception as error:
            print(error)

    @staticmethod
    def sql_execute(sql):
        try:
            # print(sql)
            conMysql.cur.execute(sql)
        except Exception as error:
            conMysql.con.rollback()
            print('insert or delete or update fail', error)
        finally:
            conMysql.con.commit()

    @staticmethod
    def selectUserInfoSql(accountType, uid, cid=0, duration_time=86400):
        if accountType == 'star_coin':  # 查询账户余额
            sql = f"select star_coin from xs_user_money where uid={uid};"
            return conMysql.sql_fetchone(sql)
        elif accountType == 'gift_num':  # 查询用户背包某个礼物总数
            sql = f'select sum(num) from xs_user_commodity where uid ={uid} and cid = {cid};'
            return conMysql.sql_fetchone(sql)
        elif accountType == 'commodity_num':  # 查询用户背包某个物品总数
            sql = f'select sum(num) from xs_user_commodity where uid ={uid} and cid = {cid} and duration_time={duration_time};'
            return conMysql.sql_fetchone(sql)
        elif accountType == 'wealth':  # 查询用户-财富值
            sql = f'select wealth from xs_user_wealth where uid ={uid};'
            return conMysql.sql_fetchone(sql)
        elif accountType == 'charm':  # 查询用户-财富值
            sql = f'select charm from xs_user_charm where uid ={uid};'
            return conMysql.sql_fetchone(sql)

    @staticmethod
    def updateMoneySql(uid, money):
        """更新用户账户余额"""
        sql = f"UPDATE xs_user_money SET star_coin={money} WHERE uid={uid};"
        conMysql.sql_execute(sql)

    @staticmethod
    def updateWealthSql(uid, wealth, pre_wealth=0):
        """更新用户-财富值"""
        sql = f"UPDATE xs_user_wealth SET wealth={wealth},pre_wealth={pre_wealth} WHERE uid={uid};"
        conMysql.sql_execute(sql)

    @staticmethod
    def updateCharmSql(uid, charm):
        """更新用户-魅力值"""
        sql = f"UPDATE xs_user_charm SET charm={charm} WHERE uid={uid};"
        conMysql.sql_execute(sql)

    @staticmethod
    def deleteUserAccountSql(tableName, uid, wid=0):
        if tableName == 'user_commodity':  # 清除用户背包数据
            sql = f"delete from xs_user_commodity where uid={uid}"
            conMysql.sql_execute(sql)
        if tableName == 'user_work_reward':  # 清除用户打赏作品的标记
            sql = f"delete from xs_user_work_reward where uid={uid} and wid={wid};"
            conMysql.sql_execute(sql)

    @staticmethod
    def insertXsUserCommodity(uid, cid, num, period_end=int(time.time() + 3600)):
        """向用户背包发礼物"""
        sql = f"INSERT INTO `xs_user_commodity` (`uid`, `cid`, `num`, `period_end`) VALUES({uid}, {cid}, {num}, {period_end});"
        conMysql.sql_execute(sql)

    @staticmethod
    def deleteProducerSinger(singer_uid):
        """
        清除的制作人/歌手的关系
        :param producer_uid: 制作人uid
        :param singer_uid: 歌手uid
        :return:
        """
        sql1 = f"update xs_audition_singer set producer_uid = 0 where uid= {singer_uid};"
        # sql2 = f"delete from xs_audition_relation where producer_uid={producer_uid} and singer_uid ={singer_uid};"
        sql2 = f"delete from xs_audition_relation where singer_uid ={singer_uid};"
        for sql in [sql1, sql2]:
            conMysql.sql_execute(sql)

    @staticmethod
    def selectProducerSinger(producer_uid):
        """
        已签约歌手人数
        :param producer_uid: 制作人uid
        :return:
        """
        sql1 = f"select count(1) from xs_audition_relation where producer_uid = {producer_uid};"
        sql2 = f"select count(1) from xs_audition_purchasing where  status=0 and uid={producer_uid}"
        total = 0
        for sql in [sql1, sql2]:
            num = conMysql.sql_fetchone(sql)
            total += num
        return total

    @staticmethod
    def updateSingerWorth(singer_uid, worth=100):
        """
        修改歌手的身价
        :param singer_uid: 歌手uid
        :param worth: 身价
        :return:
        """
        sql = f"update xs_audition_singer set worth={worth} where uid={singer_uid}"
        conMysql.sql_execute(sql)


if __name__ == '__main__':
    # conMysql.updateMoneySql(124458, 19999)
    print(conMysql.selectUserInfoSql('gift_num', 124458))
