# coding=utf-8
"""
退市K线日线接口 0x052b (仅验证日线、不复权)

参考实现: eltdx crates/eltdx-protocol/src/commands/delisted_bars.rs
请求 data(12字节): market(2) + code(6) + start(2) + count(2)
响应: count(2) + count * [date_u32(4) + 4个price_varint + volume_varint + amount_u32(4) + unknown_u32(4)]
      记录变长(因 varint), 最小 17 字节

注意: 退市K线的 volume 是 varint 原始股数(非 get_volume 浮点解码), lots = volume_raw / 100
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price, get_volume

TYPE_DELISTED_KLINES = 0x052b


class GetDelistedBarsCmd(BaseParser):
    """退市股票不复权日线"""

    def setParams(self, market, code, start=0, count=20):
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = struct.pack('<H6sHH', market, code, start, count)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_DELISTED_KLINES) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 2:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        pos = 2
        klines = []
        pre_close_milli = 0  # 上一条收盘价(毫单位)
        for i in range(count):
            if pos + 4 > len(body_buf):
                break
            (date_raw,) = struct.unpack('<I', body_buf[pos:pos + 4])
            pos += 4
            year = date_raw // 10000
            month = (date_raw // 100) % 100
            day = date_raw % 100

            open_delta, pos = get_price(body_buf, pos)
            close_delta, pos = get_price(body_buf, pos)
            high_delta, pos = get_price(body_buf, pos)
            low_delta, pos = get_price(body_buf, pos)

            open_milli = pre_close_milli + open_delta
            close_milli = open_milli + close_delta
            high_milli = open_milli + high_delta
            low_milli = open_milli + low_delta
            pre_close_milli = close_milli

            volume_raw, pos = get_price(body_buf, pos)  # varint 原始股数
            (amount_raw,) = struct.unpack('<I', body_buf[pos:pos + 4])
            pos += 4
            amount = get_volume(amount_raw)
            pos += 4  # unknown suffix

            klines.append(OrderedDict([
                ('open', open_milli / 1000.0),
                ('close', close_milli / 1000.0),
                ('high', high_milli / 1000.0),
                ('low', low_milli / 1000.0),
                ('vol', volume_raw / 100.0),
                ('amount', amount),
                ('year', year),
                ('month', month),
                ('day', day),
                ('date', '%d-%02d-%02d' % (year, month, day)),
            ]))
        return klines
