# coding=utf-8
"""
分类行情列表分页接口 0x054b

参考实现: eltdx crates/eltdx-protocol/src/commands/quotes.rs
请求 data(18字节): category(2)+sort_type(2)+start(2)+count(2)+sort_reverse(2)+5(2)+filter_raw(2)+1(2)+0(2)
响应: header(2) + count(2) + 变长记录(尾含 56 字节固定区)
按市场或板块分页返回行情列表, 可按涨幅/价格/成交额等服务端排序
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price, get_volume

TYPE_CATEGORY_QUOTES = 0x054b
CATEGORY_TAIL_SIZE = 56

# 常用分类
CATEGORY_ALIASES = {
    '沪深a股': 6, 'a股': 6, '沪深A股': 6,
}

# 常用排序
SORT_ALIASES = {
    '代码': 0x0000, '现价': 0x0006, '成交额': 0x000a, '涨幅': 0x000e,
    '封单额': 0x001c, '开盘金额': 0x001d, '涨速': 0x002e,
    '短换手': 0x00cc, '量涨速': 0x00d0, '开盘抢筹': 0x010a,
    '2分钟金额': 0x010c, '开盘涨幅': 0x0119, '最高涨幅': 0x011a,
    '最低涨幅': 0x011b, '回撤': 0x011e, '攻击': 0x011f,
}


class GetCategoryQuotesCmd(BaseParser):
    """按市场/板块分页返回行情列表(可服务端排序)"""

    def setParams(self, category, start=0, count=80, sort_type=0,
                  ascending=False, sort_reverse=None, filter_raw=0):
        if isinstance(category, str):
            category = CATEGORY_ALIASES.get(category, category)
        category = int(category)
        if isinstance(sort_type, str):
            sort_type = SORT_ALIASES.get(sort_type, sort_type)
        sort_type = int(sort_type)
        if sort_reverse is None:
            sort_reverse = 0 if sort_type == 0 else (2 if ascending else 1)
        data = struct.pack('<9H', category, sort_type, start, count,
                           sort_reverse, 5, filter_raw, 1, 0)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_CATEGORY_QUOTES) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 4:
            return []
        (header,) = struct.unpack('<H', body_buf[:2])
        (count,) = struct.unpack('<H', body_buf[2:4])
        pos = 4
        rows = []
        for i in range(count):
            if pos + 9 > len(body_buf):
                break
            market = body_buf[pos]
            code = body_buf[pos + 1:pos + 7].decode('utf-8', errors='replace')
            (active1,) = struct.unpack('<H', body_buf[pos + 7:pos + 9])
            pos += 9
            close, pos = get_price(body_buf, pos)
            pre_close_diff, pos = get_price(body_buf, pos)
            open_diff, pos = get_price(body_buf, pos)
            high_diff, pos = get_price(body_buf, pos)
            low_diff, pos = get_price(body_buf, pos)
            servertime, pos = get_price(body_buf, pos)
            neg_price, pos = get_price(body_buf, pos)
            total_hand, pos = get_price(body_buf, pos)
            current_hand, pos = get_price(body_buf, pos)
            (amount_raw,) = struct.unpack('<I', body_buf[pos:pos + 4])
            amount = get_volume(amount_raw)
            pos += 4
            inside_dish, pos = get_price(body_buf, pos)
            outer_disc, pos = get_price(body_buf, pos)
            after_outer, pos = get_price(body_buf, pos)
            open_amount, pos = get_price(body_buf, pos)
            bid1_diff, pos = get_price(body_buf, pos)
            ask1_diff, pos = get_price(body_buf, pos)
            bid_vol1, pos = get_price(body_buf, pos)
            ask_vol1, pos = get_price(body_buf, pos)
            if pos + CATEGORY_TAIL_SIZE > len(body_buf):
                break
            tail = body_buf[pos:pos + CATEGORY_TAIL_SIZE]
            pos += CATEGORY_TAIL_SIZE
            (status,) = struct.unpack('<H', tail[:2])
            (rise_speed_raw,) = struct.unpack('<h', tail[2:4])
            (short_turnover_raw,) = struct.unpack('<h', tail[4:6])
            (min2_amount,) = struct.unpack('<f', tail[6:10])
            (opening_rush_raw,) = struct.unpack('<h', tail[10:12])
            (vol_rise_speed,) = struct.unpack('<f', tail[22:26])
            (depth,) = struct.unpack('<f', tail[26:30])
            (active2,) = struct.unpack('<H', tail[54:56])
            rows.append(OrderedDict([
                ('market', market),
                ('code', code),
                ('active1', active1),
                ('active2', active2),
                ('price', self._cal(close, 0)),
                ('last_close', self._cal(close, pre_close_diff)),
                ('open', self._cal(close, open_diff)),
                ('high', self._cal(close, high_diff)),
                ('low', self._cal(close, low_diff)),
                ('servertime', servertime),
                ('vol', total_hand),
                ('cur_vol', current_hand),
                ('amount', amount),
                ('inside_dish', inside_dish),
                ('outer_disc', outer_disc),
                ('open_amount', open_amount),
                ('bid1', self._cal(close, bid1_diff)),
                ('ask1', self._cal(close, ask1_diff)),
                ('bid_vol1', bid_vol1),
                ('ask_vol1', ask_vol1),
                ('status', status),
                ('rise_speed', rise_speed_raw / 100.0),
                ('short_turnover', short_turnover_raw / 100.0),
                ('min2_amount', min2_amount),
                ('opening_rush', opening_rush_raw / 100.0),
                ('vol_rise_speed', vol_rise_speed),
                ('depth', depth),
            ]))
        return rows

    def _cal(self, base_p, diff):
        return float(base_p + diff) / 100
