# coding=utf-8
"""
代码表分页接口 0x044d (含名称/精度/昨收, 比 0x0450 字段更丰富)

参考实现: eltdx crates/eltdx-protocol/src/commands/security.rs
请求 data(14字节): market(2) + start(4) + limit(4) + 4字节0
响应: count(2) + count * record[37]:
      code(6) + multiple_u16(2) + name_gbk(16) + unknown0_f32(4)
      + decimal_u8(1) + prev_close_f32(4) + unknown3(4)
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser

TYPE_SECURITY_LIST_EX = 0x044d
CODE_RECORD_SIZE = 37


class GetSecurityListExCmd(BaseParser):
    """代码表分页(含证券名称/价格精度/昨收/量比基准)"""

    def setParams(self, market, start=0, limit=1600):
        data = struct.pack('<HII4x', market, start, limit)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_SECURITY_LIST_EX) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 2:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        pos = 2
        rows = []
        for i in range(count):
            if pos + CODE_RECORD_SIZE > len(body_buf):
                break
            rec = body_buf[pos:pos + CODE_RECORD_SIZE]
            pos += CODE_RECORD_SIZE
            code = rec[:6].decode('utf-8', errors='replace')
            (multiple,) = struct.unpack('<H', rec[6:8])
            name = rec[8:24].decode('gbk', errors='replace').rstrip('\x00').strip()
            (unknown0,) = struct.unpack('<f', rec[24:28])
            decimal = rec[28]
            (prev_close,) = struct.unpack('<f', rec[29:33])
            (unknown3,) = struct.unpack('<f', rec[33:37])
            rows.append(OrderedDict([
                ('code', code),
                ('name', name),
                ('multiple', multiple),
                ('decimal', decimal),
                ('prev_close', prev_close),
                ('volume_ratio_base', unknown0),
            ]))
        return rows
