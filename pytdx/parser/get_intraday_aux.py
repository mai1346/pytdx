# coding=utf-8
"""
分时副图数据接口 0x051b (买卖力道 / 成交对比)

参考实现: eltdx crates/eltdx-protocol/src/commands/minutes.rs
请求 data(28字节): market(2) + code(6) + 19字节0 + kind(1)
  kind: 0x00=买卖力道(buy_sell_strength), 0x0b=成交对比(volume_comparison)
响应(买卖力道): count(2) + count * [series_a_varint + series_b_varint]
响应(成交对比): count(2) + count * [prev_day_f32(4) + curr_day_f32(4)]
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price

TYPE_INTRADAY_AUX = 0x051b
KIND_BUY_SELL = 0x00
KIND_VOLUME_COMPARE = 0x0b

_MINUTE_LABELS = {}


def _minute_label(index):
    """分时索引 -> HH:MM (09:31起, 跳过午休)"""
    if index not in _MINUTE_LABELS:
        total = 571 + index if index < 120 else index + 661
        _MINUTE_LABELS[index] = '%02d:%02d' % (total // 60, total % 60)
    return _MINUTE_LABELS[index]


class GetIntradayAuxCmd(BaseParser):
    """分时副图(买卖力道/成交对比)"""

    def setParams(self, market, code, kind=KIND_BUY_SELL):
        if isinstance(code, str):
            code = code.encode('utf-8')
        self._kind = kind
        data = struct.pack('<H6s', market, code) + b'\x00' * 19 + bytes([kind])
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_INTRADAY_AUX) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 2:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        pos = 2
        rows = []
        # 用请求的 kind 判断; 若无法获取则按数据长度推断
        kind = getattr(self, '_kind', None)
        is_volume = kind == KIND_VOLUME_COMPARE
        if not is_volume and count > 0 and len(body_buf) - 2 == count * 8:
            is_volume = True
        for i in range(count):
            if is_volume:
                if pos + 8 > len(body_buf):
                    break
                (prev_day,) = struct.unpack('<f', body_buf[pos:pos + 4])
                (curr_day,) = struct.unpack('<f', body_buf[pos + 4:pos + 8])
                pos += 8
                rows.append(OrderedDict([
                    ('time', _minute_label(i)),
                    ('prev_day_vol', prev_day),
                    ('curr_day_vol', curr_day),
                ]))
            else:
                series_a, pos = get_price(body_buf, pos)
                series_b, pos = get_price(body_buf, pos)
                rows.append(OrderedDict([
                    ('time', _minute_label(i)),
                    ('buy_strength', series_a),
                    ('sell_strength', series_b),
                ]))
        return rows
