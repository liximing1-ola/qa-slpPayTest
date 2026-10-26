import gevent
from gevent import monkey

monkey.patch_all()
from common.Config import config
from common.sqlScript import mysql
from common import Consts, Logs, method
from common.basicData import encodeData
from common.method import getValue
from common.Session import Session
from Robot import robot
from common.Request import post_request_session
from common.Assert import assert_equal, assert_code
from time import sleep


class TestPayConcurrent:
    php_urL = {
        'pay_url': config.appInfo['bb_dev'] + 'pay/create?package=com.imbb.banban.android',  # 内网支付接口
        'commodity_present': config.appInfo['bb_dev'] + 'commodity/present?package=com.imbb.banban.android',  # 物品赠送接口
        'commodity_use': config.appInfo['bb_dev'] + 'commodity/use?package=com.imbb.banban.android',  # 物品使用接口
    }
    commodity_id = {
        'cid_340': 340,  # 小天使
        'cid_264': 264,  # 头像框（5h）
    }
    Session().getSession('dev')

    def startPayPackGiftReady(self):
        """
        用例描述：
        构造背包内购买礼物场景
        脚本步骤：
        1.构造购买者数据 （更新xs_user_money和xs_user_commodity）
        2.商城内购买礼物道具*1（9900*1=9900）
        3.校验【status code】和返回值【body】状态
        4.检查购买者余额 (10000-9900=100)
        5.检查背包内物品
        """
        mysql.updateMoneySql(config.payUid, 10000)
        mysql.deleteUserCommoditySql(config.payUid)
        data = encodeData(payType='shop-buy',
                          cid=self.commodity_id['cid_340'],
                          money=9900,
                          num=1)
        res = post_request_session(url=self.php_urL['pay_url'], data=data)
        assert_code(res['code'], 200)
        assert_equal(mysql.selectAllMoneySql(config.payUid), 100)
        assert_equal(mysql.checkUserAllCommoditySql(config.payUid), 1)

    def payCreateConcurrent(self):
        """
        用例描述：
        验证商城购买的道具在房间内赠送给其他人
        脚本步骤：
        1.构造打赏者和被打赏者数据
        2.打赏背包道具
        3.校验【status code】和返回值【body】状态
        4.检查背包内物品
        5.检查被打赏者余额 9900*0.62 = 6138
        """
        cid = int(mysql.getUserCommodityIdSql(self.commodity_id['cid_340'], config.payUid))
        payload = encodeData(payType='package',
                             rid=193185484,
                             uid=config.rewardUid,
                             giftId=54,  # 小天使礼物
                             money=9900,
                             package_cid=cid,
                             ctype='gift',
                             num=1)
        res = post_request_session(url=self.php_urL['pay_url'], data=payload)
        assert_code(res['code'], 200)
        getValue(res)

    def endPayCreate(self):
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_340']), 0)
        sleep(1)
        assert_equal(Consts.success_num, 1)
        Consts.fail_num = 0

    def test_01_payPackGift(self, num_times, des='打赏背包礼物的并发场景'):
        print('----------------------------------------{}----------------------------------'.format(des))
        self.startPayPackGiftReady()
        threads = []
        for i in range(num_times):
            thread = gevent.spawn(self.payCreateConcurrent)
            threads.append(thread)
        gevent.joinall(threads)
        self.endPayCreate()
        Consts.case_list_c[des] = Consts.result
        print('-----------------------------------------------------------------------------------------')

    def startCommodityUseReady(self):
        """
        用例描述：
        使用商城购买的道具
        脚本步骤：
        1.构造使用者数据
        2.校验【status code】和返回值【body】状态
        3.检查背包内物品
        """
        mysql.insertXsUserCommodity(config.payUid, self.commodity_id['cid_264'], 1)
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_264']), 1)

    def commodityUseConcurrent(self):
        cid = int(mysql.getUserCommodityIdSql(self.commodity_id['cid_264'], config.payUid))
        payload = 'id={}&num=1'.format(cid)
        res = post_request_session(url=self.php_urL['commodity_use'], data=payload)
        assert_code(res['code'], 200)
        getValue(res)
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_264']), 0)

    def endCommodityUse(self, num_times):
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_264']), 0)
        assert_equal(Consts.fail_num, num_times - 1)
        Consts.success_num = 0

    def test_02_commodityUse(self, num_times, des='使用背包物品时的并发场景'):
        print('--------------------------{}----------------------------------------------'.format(des))
        self.startCommodityUseReady()
        threads = []
        for i in range(num_times):
            thread = gevent.spawn(self.commodityUseConcurrent)
            threads.append(thread)
        gevent.joinall(threads)
        self.endCommodityUse(num_times)
        Consts.case_list_c[des] = Consts.result
        print('---------------------------------------------------------------------------------------')

    def startCommodityPresentReady(self):
        """
        用例描述：
        赠送商城购买的道具
        脚本步骤：
        1.构造使用者数据
        2.校验【status code】和返回值【body】状态
        3.检查背包内物品
        """
        mysql.updateMoneySql(config.payUid)
        mysql.updateMoneySql(config.rewardUid)
        mysql.deleteUserCommoditySql(config.payUid)
        mysql.deleteUserCommoditySql(config.rewardUid)
        mysql.insertXsUserCommodity(config.payUid, self.commodity_id['cid_264'], 2)
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_264']), 2)

    def commodityPresentConcurrent(self):
        cid = int(mysql.getUserCommodityIdSql(self.commodity_id['cid_264'], config.payUid))
        payload = 'id={}&num=1&targetId={}'.format(cid, config.rewardUid)
        res = post_request_session(url=self.php_urL['commodity_present'], data=payload)
        assert_code(res['code'], 200)
        getValue(res)

    def endCommodityPresent(self):
        assert_equal(mysql.checkUserCommoditySql(config.payUid, self.commodity_id['cid_264']), 0)
        assert_equal(mysql.checkUserCommoditySql(config.rewardUid, self.commodity_id['cid_264']), 2)
        assert_equal(Consts.success_num, 2)

    def test_03_commodityPresent(self, num_times, des='赠送物品时的并发场景'):
        print('-----------------------------------{}---------------------------------'.format(des))
        self.startCommodityPresentReady()
        threads = []
        for i in range(num_times):
            thread = gevent.spawn(self.commodityPresentConcurrent)
            threads.append(thread)
        gevent.joinall(threads)
        self.endCommodityPresent()
        Consts.case_list_c[des] = Consts.result
        print('------------------------------------------------------------------------------------')

    @staticmethod
    def startPayGiftCreateReady():
        """
        脚本步骤：
        构造购买者数据 （更新xs_user_money和xs_user_commodity）
        """
        Consts.success_num = 0
        mysql.updateMoneySql(config.payUid, 400)
        mysql.updateMoneySql(config.masterUid)

    def payGiftCreateConcurrent(self):
        """
        用例描述：
        验证房间内打赏礼物给其他人
        脚本步骤：
        1.构造打赏者和被打赏者数据
        2.礼物面板打赏礼物
        3.校验【status code】和返回值【body】状态
        4.打赏多次（>4）后，检查打赏者余额：0
        5.打赏多次（>4）后，检查被打赏者余额：400 * 0.7 = 280
        """
        payload = encodeData(payType='package',
                             money=100,
                             uid=config.masterUid,
                             giftId=config.giftId['5'])
        res = post_request_session(url=self.php_urL['pay_url'], data=payload)
        assert_code(res['code'], 200)
        getValue(res)

    @staticmethod
    def endPayGiftCreate():
        assert_equal(mysql.selectAllMoneySql(config.masterUid), 280)
        sleep(1)
        assert_equal(Consts.success_num, 4)
        Consts.fail_num = 0

    def test_04_payGift(self, num_times, des='打赏面板礼物时的并发场景'):
        print('------------------------------------{}----------------------------------'.format(des))
        self.startPayGiftCreateReady()
        threads = []
        for i in range(num_times):
            thread = gevent.spawn(self.payGiftCreateConcurrent)
            threads.append(thread)
        gevent.joinall(threads)
        self.endPayGiftCreate()
        Consts.case_list_c[des] = Consts.result
        print('-----------------------------------------------------------------------------------------')

    @staticmethod
    def startPayShopReady():
        """
        脚本步骤：
        1.构造购买者数据 （更新xs_user_money和xs_user_commodity）
        """
        Consts.success_num = 0
        mysql.updateMoneySql(config.payUid, 40000)
        mysql.deleteUserCommoditySql(config.payUid)

    def payShopCreateConcurrent(self):
        """
        用例描述：
        验证商城购买道具
        脚本步骤：
        1.构造打赏者和被打赏者数据
        2.打赏背包道具
        3.校验【status code】和返回值【body】状态
        4.检查背包内物品
        """
        data = encodeData(payType='shop-buy',
                          cid=self.commodity_id['cid_340'],
                          money=9900,
                          num=1)
        res = post_request_session(url=self.php_urL['pay_url'], data=data)
        assert_code(res['code'], 200)
        getValue(res)

    @staticmethod
    def endPayShopCreate():
        assert_equal(mysql.selectAllMoneySql(config.payUid), 400)
        assert_equal(mysql.checkUserAllCommoditySql(config.payUid), 4)
        sleep(1)
        assert_equal(Consts.success_num, 4)
        Consts.fail_num = 0

    def test_05_payShop(self, num_times, des='购买商城礼物时的并发场景'):
        print('----------------------------------------{}----------------------------------'.format(des))
        self.startPayShopReady()
        threads = []
        for i in range(num_times):
            thread = gevent.spawn(self.payShopCreateConcurrent)
            threads.append(thread)
        gevent.joinall(threads)
        self.endPayShopCreate()
        Consts.case_list_c[des] = Consts.result
        print('-----------------------------------------------------------------------------------------')

    def main(self, num):
        self.test_01_payPackGift(num)
        #self.test_02_commodityUse(num)
        #self.test_03_commodityPresent(num)
        #self.test_04_payGift(num)
        #self.test_05_payShop(num)
        case_list = method.dictToList(Consts.case_list_c)
        des = "{}\n".format(case_list)
        Logs.get_log('concurrentCaseResult.log').info(des)
        robot('wxBot', reason=des)


if __name__ == '__main__':
    p = TestPayConcurrent()
    p.main(21)
