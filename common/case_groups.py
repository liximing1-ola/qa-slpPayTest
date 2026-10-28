# coding=utf-8
"""用例模块 → 业务场景族，让报告能回答「哪一类在退化」

本来打算给每条用例打标签（房间类型/身份/支付方式），但看完全部 166 条 des 就
明白这条路走不通：逗号前的「场景」段有 46 种写法，没有统一结构，逐条标注既
要改 166 处，又完全依赖自觉——漏标的那条不会出现在统计里，比没有统计更糟，
因为它会让人误以为「这类没问题」。

文件名本身就是场景族，而且这个信号已经存在：test_gs_room 里全是「GS 房间打赏」，
test_coupon 里全是券，test_gs_other_broker_* 里全是跨档公会分成。它不会漂移、
不需要维护。所以先按模块分组：新开一个用例文件时加一行，pre_push_audit 第 9 类
会检查漏登记。

以后要细分「跨档 / 非跨档」「单礼物 / 多礼物」这类横切维度，再用 des 上的约定
格式做，那时这张表已经提供了骨架。

注意 caseSlp 与 caseXsg 有同名模块（test_gs_room / test_normal_room / test_exp 等），
这里按模块名统一映射：两个 App 的同名文件描述的是同一类业务场景，一次只跑一个
App，不会同时出现在报告里。caseStress 是独立入口的并发与幂等用例，同样在这里登记，
这样它的报告也能按场景族统计。
"""

UNGROUPED = '未分组'

# 模块名（去掉 caseSlp./caseXsg. 前缀）→ 场景族
GROUPS = {
    'test_001': '基础造数',
    'test_check': '边界与扣费顺序',
    'test_coupon': '优惠券·有损',
    'test_coupon_2': '优惠券·无损',
    'test_exp': '经验值与加速卡',
    'test_gs_broker_room_new': '公会分成·非跨档',
    'test_gs_chat': 'GS·私聊打赏',
    'test_gs_defend': 'GS·个人守护',
    'test_gs_other_broker_cplink_play_room_new': '公会分成·跨档·连连看踢保',
    'test_gs_other_broker_room_new': '公会分成·跨档·非派单',
    'test_gs_other_broker_slporder_room_new': '公会分成·跨档·派单',
    'test_gs_pay_self': 'GS·自刷',
    'test_gs_room': 'GS·房间打赏',
    'test_gs_room_defend': 'GS·房间守护',
    'test_gs_room_pay_self': 'GS·房间自刷',
    'test_many_people_room': '多人打赏',
    'test_naming_song': '点唱与冠歌',
    'test_normal_chat': '普通用户·私聊打赏',
    'test_normal_defend': '普通用户·个人守护',
    'test_normal_pay_self': '普通用户·自刷',
    'test_normal_room': '普通用户·房间打赏',
    'test_normal_room_pay_self': '普通用户·房间自刷',
    'test_pay_concurrent': '并发与幂等',
    'test_pretty_room': '靓号房',
    'test_repeat_submit': '并发与幂等',
    'test_starship': '星舰',
    'test_zx_box': '甄选礼盒',
}


def module_of(case):
    """caseSlp.test_gs_room.TestGs.test_001 -> test_gs_room

    类级钩子（setUpClass/tearDownClass）报错时 unittest 传进来的是 _ErrorHolder，
    id 形如 "setUpClass (caseSlp.test_gs_room.TestGs)"，按点切分后第二段仍是模块名，
    所以这类报错也能归到正确的场景族。
    """
    parts = case.id().split('.')
    if len(parts) < 2 or not parts[1].startswith('test_'):
        return ''
    return parts[1]


def group_of(case):
    """用例所属的场景族；取不到时归「未分组」，不能让统计悄悄漏掉"""
    return GROUPS.get(module_of(case), UNGROUPED)
