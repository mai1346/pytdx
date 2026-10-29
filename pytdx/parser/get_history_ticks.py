# coding=utf-8
"""
历史成交明细增强接口 0x0fc6

参考实现: eltdx crates/eltdx-protocol/src/commands/trades.rs
请求 data(16字节): date(4) + market(2) + code(6) + start(2) + count(2)
响应: count(2) + price_base_f32(4) + 变长记录[time_u16(2) + price_delta_varint
      + volume_varint + order_count_varint + status_varint + tail_varint]
价格累计: price_acc += price_delta; price = price_acc / 100
status: 0=买, 1=卖, 2=中性, 8=竞价快照; time=565(09:25) 为开盘撮合
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price

TYPE_HISTORY_TICKS = 0x0fc6

SIDE_NAMES = {0: 'buy', 1: 'sell', 2: 'neutral'}


def _minute_label(minutes):
    return '%02d:%02d' % (minutes // 60, minutes % 60)


class GetHistoryTicksCmd(BaseParser):
    """历史成交明细增强分页 (0x0fc6), 比 0x0fb5 字段更丰富"""

    def setParams(self, market, code, date, start=0, count=900):
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = struct.pack('<IH6sHH', date, market, code, start, count)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_HISTORY_TICKS) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 6:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        (price_base,) = struct.unpack('<f', body_buf[2:6])
        pos = 6
        rows = []
        price_acc = 0
        for i in range(count):
            if pos + 2 > len(body_buf):
                break
            (time_min,) = struct.unpack('<H', body_buf[pos:pos + 2])
            pos += 2
            price_delta, pos = get_price(body_buf, pos)
            volume, pos = get_price(body_buf, pos)
            order_count, pos = get_price(body_buf, pos)
            status, pos = get_price(body_buf, pos)
            tail, pos = get_price(body_buf, pos)
            price_acc += price_delta
            rows.append(OrderedDict([
                ('time', _minute_label(time_min)),
                ('time_minutes', time_min),
                ('price', price_acc / 100.0),
                ('vol', volume),
                ('order_count', order_count),
                ('status', status),
                ('side', SIDE_NAMES.get(status, 'status_%d' % status)),
                ('is_auction', status == 8),
                ('is_opening_match', time_min == 9 * 60 + 25),
            ]))
        return rows
