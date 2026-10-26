import redis
from typing import Union, List, Dict, Any, Optional


class conRedis:
    """Redis 客户端封装，提供�?key(s) 为核心的增删改查操作"""

    redis_config = {
        'host_slp': '192.168.1.24',  # slp测试服务�?redis
        'port': 6379  # 端口
    }

    _pools = {}

    @classmethod
    def getConn(cls, host: str = None) -> redis.Redis:
        """获取 Redis 连接（带连接池缓存）"""
        if host is None:
            host = cls.redis_config['host_slp']

        if host not in cls._pools:
            pool = redis.ConnectionPool(
                host=host,
                port=cls.redis_config['port'],
                decode_responses=True
            )
            cls._pools[host] = redis.Redis(connection_pool=pool)

        return cls._pools[host]

    # ========== 字符串操作（增删改查�?=========

    @staticmethod
    def set(key: str, value: Union[str, int, float], ex: int = None) -> bool:
        """新增/修改字符串键�?        :param key: 键名
        :param value: 键�?        :param ex: 过期时间（秒�?        """
        r = conRedis.getConn()
        return r.set(key, value, ex=ex)

    @staticmethod
    def get(key: str) -> Optional[str]:
        """查询字符串键�?        :param key: 键名
        :return: 键值，不存在返�?None
        """
        r = conRedis.getConn()
        return r.get(key)

    @staticmethod
    def mset(mapping: Dict[str, Any]) -> bool:
        """批量新增/修改键�?        :param mapping: 键值字典，�?{'key1': 'val1', 'key2': 'val2'}
        """
        r = conRedis.getConn()
        return r.mset(mapping)

    @staticmethod
    def mget(keys: List[str]) -> List[Optional[str]]:
        """批量查询键�?        :param keys: 键名列表
        :return: 键值列�?        """
        r = conRedis.getConn()
        return r.mget(keys)

    # ========== 删除操作 ==========

    @staticmethod
    def delete(*keys: str) -> int:
        """删除一个或多个�?        :param keys: 一个或多个键名
        :return: 成功删除的键数量
        """
        r = conRedis.getConn()
        return r.delete(*keys)

    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """按模式删除键（如 'prefix:*'�?        :param pattern: 匹配模式
        :return: 成功删除的键数量
        """
        r = conRedis.getConn()
        matching_keys = r.keys(pattern)
        if matching_keys:
            return r.delete(*matching_keys)
        return 0

    # ========== Hash 操作（增删改查）==========

    @staticmethod
    def hset(key: str, field: str, value: Union[str, int, float]) -> int:
        """新增/修改 Hash 字段
        :param key: Hash 键名
        :param field: 字段�?        :param value: 字段�?        """
        r = conRedis.getConn()
        return r.hset(key, field, value)

    @staticmethod
    def hget(key: str, field: str) -> Optional[str]:
        """查询 Hash 字段
        :param key: Hash 键名
        :param field: 字段�?        :return: 字段值，不存在返�?None
        """
        r = conRedis.getConn()
        return r.hget(key, field)

    @staticmethod
    def hdel(key: str, *fields: str) -> int:
        """删除 Hash 中的一个或多个字段
        :param key: Hash 键名
        :param fields: 一个或多个字段�?        :return: 成功删除的字段数�?        """
        r = conRedis.getConn()
        return r.hdel(key, *fields)

    @staticmethod
    def hgetall(key: str) -> Dict[str, str]:
        """查询 Hash 所有字�?        :param key: Hash 键名
        :return: 字段字典
        """
        r = conRedis.getConn()
        return r.hgetall(key)

    # ========== 辅助查询 ==========

    @staticmethod
    def keys(pattern: str) -> List[str]:
        """按模式查询键列表
        :param pattern: 匹配模式，如 'prefix:*'
        :return: 匹配的键列表
        """
        r = conRedis.getConn()
        return r.keys(pattern)

    @staticmethod
    def exists(*keys: str) -> int:
        """查询键是否存�?        :param keys: 一个或多个键名
        :return: 存在的键数量
        """
        r = conRedis.getConn()
        return r.exists(*keys)

    @staticmethod
    def expire(key: str, seconds: int) -> bool:
        """修改键过期时�?        :param key: 键名
        :param seconds: 过期秒数
        """
        r = conRedis.getConn()
        return r.expire(key, seconds)

    @staticmethod
    def ttl(key: str) -> int:
        """查询键剩余生存时�?        :param key: 键名
        :return: 剩余秒数�?1 表示永不过期�?2 表示键不存在
        """
        r = conRedis.getConn()
        return r.ttl(key)

    # ========== 兼容旧方�?==========

    @staticmethod
    def checkSetKey(key, value):
        """兼容旧方法：集合键不存在时才添加"""
        r = conRedis.getConn()
        if r.scard(key) == 0:
            r.sadd(key, value)

    @staticmethod
    def delKey(key, *values):
        """兼容旧方法：删除 Hash 字段"""
        r = conRedis.getConn()
        for value in values:
            for k in value:
                r.hdel(key, k)

    @staticmethod
    def delKey_slp(pattern):
        """兼容旧方法：按模式删除（请优先使�?delete_pattern�?""
        r = conRedis.getConn()
        matching_keys = r.keys(pattern)
        if matching_keys:
            deleted_count = r.delete(*matching_keys)
            print(f"Deleted {deleted_count} keys matching '{pattern}'")
            return deleted_count
        else:
            print("No keys found matching the pattern")
            return 0

    @staticmethod
    def key_test():
        """测试示例"""
        r = conRedis.getConn()
        r.set('counter', 100)
        r.incr('counter')
        print(r.get('counter'))


if __name__ == '__main__':
    # ========== String 增删改查示例 ==========
    conRedis.set('test:string', 'hello', ex=60)
    print('get:', conRedis.get('test:string'))
    conRedis.mset({'test:k1': 'v1', 'test:k2': 'v2'})
    print('mget:', conRedis.mget(['test:k1', 'test:k2']))
    conRedis.delete('test:string', 'test:k1', 'test:k2')

    # ========== Hash 增删改查示例 ==========
    conRedis.hset('test:hash', 'name', 'Alice')
    print('hget:', conRedis.hget('test:hash', 'name'))
    conRedis.hset('test:hash', 'age', 18)
    print('hgetall:', conRedis.hgetall('test:hash'))
    conRedis.hdel('test:hash', 'age')
    conRedis.delete('test:hash')

    # ========== 辅助查询示例 ==========
    conRedis.set('test:ttl', 'value', ex=120)
    print('exists:', conRedis.exists('test:ttl'))
    print('ttl:', conRedis.ttl('test:ttl'))
    print('keys:', conRedis.keys('test:*'))
    conRedis.delete_pattern('test:*')
