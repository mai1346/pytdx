# coding=utf-8
"""
近期历史分时图接口 0x0feb

参考实现: eltdx crates/eltdx-protocol/src/commands/minutes.rs
请求 data(11字节): date_selector_u32(4) + market(1) + code(6)
  date_selector = 0xfed62304 - date_ordinal
  date_ordinal 采用 (year-1)*365 + 闰年数 + 月内累计天数的 proleptic 序数
响应: count(2) + prev_close_f32(4) + open_f32(4)
      + 变长记录[price_varint + avg_varint + volume_varint]
  首条 price/avg 为绝对值, 后续为相对首条的增量
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price

TYPE_RECENT_INTRADAY = 0x0feb
RECENT_DATE_SELECTOR_BASE = 0xfed62304

_DAYS_BEFORE_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
_MINUTE_LABELS = {}


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _date_ordinal(year, month, day):
    """eltdx python_date_ordinal 的 Python 移植"""
    prev = year - 1
    ordinal = prev * 365 + prev // 4 - prev // 100 + prev // 400
    ordinal += _DAYS_BEFORE_MONTH[month - 1] + day
    if month > 2 and _is_leap(year):
        ordinal += 1
    return ordinal


def _minute_label(index):
    if index not in _MINUTE_LABELS:
        total = 571 + index if index < 120 else index + 661
        _MINUTE_LABELS[index] = '%02d:%02d' % (total // 60, total % 60)
    return _MINUTE_LABELS[index]


class GetRecentIntradayCmd(BaseParser):
    """近期窗口内的历史分时(适合查较近交易日的分钟走势)"""

    def setParams(self, market, code, date):
        """date: (year, month, day) 或 YYYYMMDD 整数"""
        if isinstance(date, int):
            year = date // 10000
            month = (date // 100) % 100
            day = date % 100
        else:
            year, month, day = date
        ordinal = _date_ordinal(year, month, day)
        selector = (RECENT_DATE_SELECTOR_BASE - ordinal) & 0xffffffff
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = struct.pack('<I', selector) + bytes([market]) + code
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_RECENT_INTRADAY) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 10:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        (prev_close,) = struct.unpack('<f', body_buf[2:6])
        (open_price,) = struct.unpack('<f', body_buf[6:10])
        pos = 10
        rows = []
        first_price = first_avg = None
        for i in range(count):
            price_field, pos = get_price(body_buf, pos)
            avg_field, pos = get_price(body_buf, pos)
            volume, pos = get_price(body_buf, pos)
            if i == 0:
                first_price = price_field
                first_avg = avg_field
                price_raw = price_field
                avg_raw = avg_field
            else:
                price_raw = first_price + price_field
                avg_raw = first_avg + avg_field
            rows.append(OrderedDict([
                ('time', _minute_label(i)),
                ('price', price_raw / 1000.0),
                ('avg_price', avg_raw / 10000.0),
                ('vol', volume),
            ]))
        return {'prev_close': prev_close, 'open': open_price, 'points': rows}
