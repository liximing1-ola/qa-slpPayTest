import time
import random
import hashlib
import base64
from urllib.parse import quote, urlencode


class getToken:

    def __init__(self, uid, _salt):
        self.uid = uid
        self._salt = _salt
        self._KEY = "^&(tre)%29^*"
        self._EXPIRY = 2592000
        self._chars = '01234567890abcdefghijklmnopqrstuvwxyz'
        self._verify_salt = '5(d+V8cxpY%d'
        self._key_c_length = 4

    def get_token(self):
        arg_dict = {
            "u": self.uid,
            "s": self._salt,
            "p": "app",
            "t": int(time.time()),
            "c": ""
        }
        string = urlencode(arg_dict)
        digests = getToken.md5(string + self._verify_salt).lower()
        data = string + digests[0:5]
        key = getToken.md5(self._KEY)
        key_a = getToken.md5(key[0:16])
        key_b = getToken.md5(key[16:32])
        key_c = getToken.md5(getToken.php_microtime())[-4:]
        crypt_key = key_a + getToken.md5(key_a + key_c)
        key_length = len(crypt_key)
        data = str("%010d" % (int(time.time()) + self._EXPIRY)) + getToken.md5(data + key_b)[0:16] + data

        data_length = len(data)

        box = [i for i in range(0, 256)]
        rndkey = [0 for _ in range(0, 256)]

        for i in range(0, 256):
            rndkey[i] = ord(crypt_key[i % key_length])

        j = 0
        for i in range(0, 256):
            j = (j + box[i] + rndkey[i]) % 256
            box[i], box[j] = box[j], box[i]

        a = j = 0
        result = ""
        for i in range(0, data_length):
            a = (a + 1) % 256
            j = (j + box[a]) % 256
            box[a], box[j] = box[j], box[a]
            result += chr(ord(data[i]) ^ (box[(box[a] + box[j]) % 256]))

        token = quote(
            key_c + str(base64.b64encode(bytes(result, encoding='latin1')), encoding='latin1')
            .replace("=", "")).replace("/", "%2F").replace("%", "__")

        return token

    @staticmethod
    def get_salt():
        _chars = '01234567890abcdefghijklmnopqrstuvwxyz'
        max_length = len(_chars) - 1
        hash_s = ''
        for i in range(0, 10):
            hash_s += _chars[random.randint(0, max_length)]
        return hash_s

    @staticmethod
    def md5(s):
        m = hashlib.md5(bytes(s, encoding='utf-8'))
        return m.hexdigest()

    @staticmethod
    def php_microtime():
        t = time.time()
        s, m = str(t).split(".")
        m = str(float(m) / (10 ** len(m))).ljust(10, "0")
        return m + " " + s


if __name__ == "__main__":
    get_token = getToken(100287189, getToken.get_salt())
    print(get_token.get_token())
    #  处理礼物打赏并发场景
