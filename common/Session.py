# coding=utf-8
"""
封装获取cookie方法
"""
import json
import os
import requests
import urllib3
from common import Logs, method
from common.Config import config
from common.paramsYaml import Yaml


class Session:
	def __init__(self):
		self.config = config

	@staticmethod
	def getSession(env):
		"""
		获取qq登陆session（默认uid�?		:param env: 环境
		:return: 登陆token
		"""
		urllib3.disable_warnings()
		urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
		if env == config.appName['不夜星球']:
			print("slp")
			from caseSlp.config import payUid, gsUid, gs_B_uid
			from caseSlp.tools import get_test_token
		elif env == config.appName['小拾�?]:
			print("xsg")
			from caseXsg.config import payUid, gsUid, gs_B_uid_1 as gs_B_uid
			from caseXsg.tools import get_test_token
		else:
			print("env input error")
			return None
		try:
			token_map = get_test_token(payUid, gsUid, gs_B_uid)
			for uid, token in token_map.items():
				Session.checkUserToken('write', app_name=env, uid=uid, token=token)
			return {'token': token_map[payUid], 'uid': payUid}
		except Exception as error:
			Logs.get_log('getSession.log').error('默认方案session异常，原因： {}'.format(error))
			from common.conSlpXsgMysql import conMysql
			from common.getToken import getToken
			token = getToken(payUid, conMysql.selectUserInfoSql('user_index', payUid)).get_token()
			tokenDict = {'token': token, 'uid': payUid}
			print('默认方案失败，启用备选方案：token:{}'.format(token))
			Session.checkUserToken('write', app_name=env, uid=None, token=tokenDict['token'])
			return tokenDict

	@staticmethod
	def checkUserToken(operate, app_name='dev', uid=None, token=''):
		txtPath = os.path.split(os.path.realpath(__file__))[0] + '/{}UserToken.txt'.format(app_name)
		key = str(uid) if uid is not None else 'default'
		if not os.path.exists(txtPath):
			open(txtPath, 'w', encoding='utf-8').close()
		if operate == 'write':
			token_data = {}
			if os.path.exists(txtPath) and os.path.getsize(txtPath) > 0:
				with open(txtPath, 'r', encoding='utf-8') as f:
					token_data = json.loads(f.read())
			token_data[key] = token
			with open(txtPath, 'w', encoding='utf-8') as f:
				json.dump(token_data, f, ensure_ascii=False)
				f.flush()
		elif operate == 'read':
			with open(txtPath, 'r', encoding='utf-8') as f:
				content = f.read()
				if not content:
					raise Exception(f"{txtPath},token为空!")
				token_data = json.loads(content)
				result = token_data.get(key, '')
				if not result and key != 'default':
					result = token_data.get('default', '')
				if not result:
					raise Exception(f"{txtPath},key={key}的token为空!")
				return result
