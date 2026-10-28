# -*- coding: utf-8 -*-
"""
兼容转发模块：实现已合并到 common/tools.py

caseSlp/tools.py 与 caseXsg/tools.py 原本各存一份几乎相同的实现（240 行 / 217 行），
改动时很容易只改一边。现在统一由 common/tools.py 维护，这里只做重新导出，
保持用例里 `from caseXsg.tools import xxx` 的写法不变。
"""
from common.tools import (  # noqa: F401
    merge_dicts,
    create_sign,
    hash_key,
    deal_num,
    get_test_token,
    check_vip_pop,
    prepare_test_data,
    prepare_vip_pop_data,
    read_vip_pop,
    prepare_room_data,
    prepare_acceleration_card,
    clear_acceleration_card,
    insert_coupon,
    insert_package_gift,
    get_last_weekday_timestamp,
    XsgTravelerMixin,
)
