# coding=utf-8
"""
特殊品种涨跌停限制表接口 0x0452

参考实现: eltdx crates/eltdx-protocol/src/commands/limits.rs
请求 data(14字节): start_index(2) + 12字节0
响应: count(2) + count * [market(1) + code_num_u32(4) + upper_f32(4) + lower_f32(4)]  每条 13 字节
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser

TYPE_SPECIAL_LIMITS = 0x0452
LIMIT_RECORD_SIZE = 13


class GetSpecialLimitsCmd(BaseParser):
    """特殊品种涨跌停限制表, 需按表扫描后本地索引到具体代码"""

    def setParams(self, start=0):
        data = struct.pack('<H', start) + b'\x00' * 12
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_SPECIAL_LIMITS) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 2:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        pos = 2
        rows = []
        for i in range(count):
            if pos + LIMIT_RECORD_SIZE > len(body_buf):
                break
            market_id = body_buf[pos]
            (code_num,) = struct.unpack('<I', body_buf[pos + 1:pos + 5])
            (upper,) = struct.unpack('<f', body_buf[pos + 5:pos + 9])
            (lower,) = struct.unpack('<f', body_buf[pos + 9:pos + 13])
            pos += LIMIT_RECORD_SIZE
            rows.append(OrderedDict([
                ('market', market_id),
                ('code', '%06d' % code_num),
                ('upper_limit', upper),
                ('lower_limit', lower),
            ]))
        return rows
