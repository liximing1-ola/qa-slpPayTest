#!/usr/bin/env python
# -*- coding: utf-8 -*-
#  @author: WuBingBing
from common.Config import config
from common.Request import post_request_session
from common.conPtMysql import conMysql
import time
import random


class Greedy:

    @staticmethod
    def greedy_index(uid):
        url = 'greedy/index?uid={}'.format(uid)
        return post_request_session(config.pt_host + url, None, tokenName='pt')

    @staticmethod
    def greedy_stake(uid, vid, counter, round_id, money_type, notice=False):
        url = 'greedy/stake?uid={}'.format(uid)
        params = {
            'vid': vid,
            'counter': counter,
            'round_id': round_id,
            'money_type': money_type,
            'notice': notice
        }
        return post_request_session(config.pt_host + url, params, tokenName='pt')

    @staticmethod
    def bet(money_type):
        try:
            # 获取摩天轮信息
            greed_round_id = 0
            greed_counter = []
            for i in range(10):
                greed_index = Greedy.greedy_index(config.pt_payUid)
                greed_state = greed_index['body']['data']['state']
                if greed_state == '1':
                    greed_round_id = greed_index['body']['data']['round_id']
                    greed_counter = greed_index['body']['data']['counter_range']
                    break
                else:
                    time.sleep(5)  # 等待摩天轮变为可投注状态
                    continue

            # 下注
            for i in range(6):
                greed_vid = random.randint(1, 8)
                Greedy.greedy_stake(config.pt_payUid, greed_vid, greed_counter, greed_round_id, money_type)

            # 获取开奖数据
            greed_counter_all = 0
            greedy_prize = 0
            for i in range(10):
                greedy_player_data = conMysql.select_greedy_prize(config.pt_payUid, greed_round_id)
                if greedy_player_data == 0:
                    time.sleep(5)  # 等待摩天轮开奖
                    continue
                else:
                    greed_counter_all = greedy_player_data[0]
                    greedy_prize = greedy_player_data[1]
                    break
            if greed_counter_all > 0:
                return [greed_counter_all, greedy_prize]
            else:
                return [0, 0]
        except Exception as e:
            print(e)
