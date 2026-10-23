import gevent
from gevent import monkey

monkey.patch_all()
import requests
from common.basicData import encodeData


class PayConcurrent:
    url = "https://api-new.yinjietd.com/pay/create?package=com.imbb.banban.android&_ipv=0&_platform=android&_index=1755&_model=SEA-AL10&_timestamp=1676458178&_sign=bfd82709d13088a721188e59c0342638"
    commodity_id_url = 'https://api-new.yinjietd.com/commodity/userList?version=3&type=gift&package=com.imbb.banban.android&_ipv=0&_platform=android&_index=157&_model=SEA-AL10&_timestamp=1676621169&_sign=fba57be89a5882903e2458d55017145d'

    headers = {
            'user-token': 'c1df__2FUoyoWc8SXjYWNHA7oA__2Bkszd8LIfgkon__2BvnHKN5LYp0gJSJS__2FWuc77sC__2F5ci2Q5xBcqjv1k52IUDseppM__2B__2Bm8tvk2xzk__2F1__2F10Uhn8PUASP7ibuVKRLQO',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def release_test(self):
        payload = encodeData(payType='package',
                             rid=118491893,
                             uid=100287189,
                             giftId=69,  # 修改id
                             money=100,
                             package_cid=self.getCommodityId(),  # 修改id
                             ctype='gift')

        response = requests.request("POST", self.url, headers=self.headers, data=payload)
        print(response.json())

    def release_test2(self):
        threads = []
        for i in range(20):
            thread = gevent.spawn(self.release_test)
            threads.append(thread)
        gevent.joinall(threads)

    def getCommodityId(self):
        res = requests.get(self.commodity_id_url, headers=self.headers).json()
        if res['success'] == 0 or len(res['data']) == 0:
            return 0

        return res['data'][0]['id']


if __name__ == '__main__':
    p = PayConcurrent()
    p.release_test2()
