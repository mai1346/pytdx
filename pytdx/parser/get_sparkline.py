# coding=utf-8
"""
小走势图接口 0x0fd1

参考实现: eltdx crates/eltdx-protocol/src/commands/minutes.rs
请求 data(37字节): market(1)+0 + code(6) + 16字节0 + selector(1)+0
      + window_u16(2) + fixed_u32(4) + 5字节0
响应: market(1)+0+code(6)+16字节0+selector(1)+0+reserved_u32(4)+0_u32(4)
      + max_count_u16(2) + base_f32(4) + price_count_u16(2) + prices[f32...]
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser

TYPE_SPARKLINE = 0x0fd1
DEFAULT_SPARKLINE_SELECTOR = 1
DEFAULT_SPARKLINE_WINDOW = 20
DEFAULT_SPARKLINE_FIXED = 0x01000000


class GetSparklineCmd(BaseParser):
    """单标的小型价格走势序列(适合列表页概览小图)"""

    def setParams(self, market, code, selector=DEFAULT_SPARKLINE_SELECTOR,
                  window=DEFAULT_SPARKLINE_WINDOW, fixed=DEFAULT_SPARKLINE_FIXED):
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = bytearray([market, 0])
        data += code
        data += b'\x00' * 16
        data += bytes([selector, 0])
        data += struct.pack('<H', window)
        data += struct.pack('<I', fixed)
        data += b'\x00' * 5
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_SPARKLINE) + bytes(data)

    def parseResponse(self, body_buf):
        if len(body_buf) < 42:
            return []
        code = body_buf[2:8].decode('utf-8', errors='replace')
        (max_count,) = struct.unpack('<H', body_buf[34:36])
        (base_price,) = struct.unpack('<f', body_buf[36:40])
        (price_count,) = struct.unpack('<H', body_buf[40:42])
        prices = []
        pos = 42
        for i in range(price_count):
            if pos + 4 > len(body_buf):
                break
            (v,) = struct.unpack('<f', body_buf[pos:pos + 4])
            prices.append(v)
            pos += 4
        return OrderedDict([
            ('code', code),
            ('max_count', max_count),
            ('base_price', base_price),
            ('prices', prices),
        ])
