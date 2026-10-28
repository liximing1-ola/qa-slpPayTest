"""
用例公共小工具

历史遗留的 dictToList / dictToListSlack / getValue / checkPath / getUserTitle / reason_slp
已确认全仓库零引用（并发脚本删掉后就没人调了），这里一并移除；
checkPath 还引用着已下线项目的 'PT' 机器人，属于会直接报错的死代码。

getImage 也随通知里的 icon 配图模式一并删除：它唯一调用方是 Robot.py 的 icon 分支，
而那个分支同样已无人调用。同时带走一处硬编码：mxnzp 图片接口的 app_id / app_secret
原来直接写在 URL 里，等于凭据进仓库。
"""


# 检查当前字段是否在Json中存在
def isExtend(data, tag):
    if type(data) != type({}):
        print('please input a json!')
    else:
        key_list = getKeys(data)
        for key in key_list:
            if key == tag:
                return True
    return False


def getKeys(data):
    keysAll_list = []

    def getKey(json_data):  # 遍历json所有key
        if type(json_data) == type({}):
            keys = json_data.keys()
            for key in keys:
                value = json_data.get(key)
                if type(value) != type({}) and type(value) != type([]):
                    keysAll_list.append(key)
                elif type(value) == type({}):
                    keysAll_list.append(key)
                    getKey(value)
                elif type(value) == type([]):
                    keysAll_list.append(key)
                    for para in value:
                        if type(para) == type({}) or type(para) == type([]):
                            getKey(para)
                        else:
                            keysAll_list.append(para)

    getKey(data)
    return keysAll_list


def reason(des, res):
    body = res.get('body') if isinstance(res, dict) else None
    if isinstance(body, dict) and body.get('success') == 0 and not isExtend(body, 'msg'):
        print(body)
    return 'Depiction: {},  failReason: {}'.format(des, body)
