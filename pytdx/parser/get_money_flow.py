# coding=utf-8
"""
资金流向日数据接口 0x0ffc (ASK_OneZJLX 服务)

参考实现: eltdx crates/eltdx-protocol/src/commands/money_flow.rs
注意: 该服务使用 legacy 路由, msg_id 编码 route(0x7e)|channel(0x2d)|seq
请求 data(38字节): market(1) + 0(1) + code(6) + 补零到 38 字节
响应: header(0x28=40字节) + count * record[0x58=88字节]
      record: date_u32(4) + 21个u32(84) = 88
主力和分档净额由 16 个 bucket(从 raw[10..17] 拆出) 计算
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser

TYPE_MONEY_FLOW = 0x0ffc
MONEY_FLOW_HEADER_SIZE = 0x28
MONEY_FLOW_RECORD_SIZE = 0x58
MONEY_FLOW_REQUEST_DATA_SIZE = 38
MONEY_FLOW_ROUTE = 0x7e
MONEY_FLOW_CHANNEL = 0x2d


class GetMoneyFlowCmd(BaseParser):
    """个股资金流向日数据(主力/超大单/大单/中单/小单净额)"""

    def setParams(self, market, code, seq=0x5e):
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = bytearray([market, 0])
        data += code
        data += b'\x00' * (MONEY_FLOW_REQUEST_DATA_SIZE - len(data))
        length = len(data) + 2
        # msg_id 编码路由: seq | (channel << 8) | (route << 16)
        wire_msg_id = (seq & 0xff) | (MONEY_FLOW_CHANNEL << 8) | (MONEY_FLOW_ROUTE << 16)
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, wire_msg_id, 0x01,
                                    length, length, TYPE_MONEY_FLOW) + bytes(data)

    def parseResponse(self, body_buf):
        if len(body_buf) < MONEY_FLOW_HEADER_SIZE:
            return []
        rows = []
        pos = 0
        while pos < len(body_buf):
            header = body_buf[pos:pos + MONEY_FLOW_HEADER_SIZE]
            if len(header) < MONEY_FLOW_HEADER_SIZE:
                break
            market_id = header[0]
            code = header[2:8].decode('utf-8', errors='replace')
            (reported_count,) = struct.unpack('<H', header[0x26:0x28])
            rec_start = pos + MONEY_FLOW_HEADER_SIZE
            available = (len(body_buf) - rec_start) // MONEY_FLOW_RECORD_SIZE
            count = reported_count if reported_count else available
            for i in range(count):
                off = rec_start + i * MONEY_FLOW_RECORD_SIZE
                if off + MONEY_FLOW_RECORD_SIZE > len(body_buf):
                    break
                rows.append(self._parse_record(market_id, code, body_buf[off:off + MONEY_FLOW_RECORD_SIZE]))
            pos = rec_start + count * MONEY_FLOW_RECORD_SIZE
        return rows

    def _parse_record(self, market_id, code, rec):
        (date_raw,) = struct.unpack('<I', rec[:4])
        raw = list(struct.unpack('<21I', rec[4:88]))
        (total_amount,) = struct.unpack('<f', rec[8:12])  # = raw[1] as f32
        # 16 buckets: 从 raw[10..17] 每个u32拆低16/高16
        buckets = [0] * 16
        for i in range(8):
            packed = raw[10 + i]
            buckets[i * 2] = packed & 0xffff
            buckets[i * 2 + 1] = (packed >> 16) & 0xffff
        scale = float(total_amount) / 50000.0
        bucket = (buckets[0] - buckets[1] + buckets[4] - buckets[5])
        main_buy_bucket = (buckets[2] - buckets[3] + buckets[6] - buckets[7]
                           + buckets[10] - buckets[11] + buckets[14] - buckets[15])
        year = date_raw // 10000
        month = (date_raw // 100) % 100
        day = date_raw % 100
        return OrderedDict([
            ('market', market_id),
            ('code', code),
            ('date', '%d-%02d-%02d' % (year, month, day)),
            ('total_amount', float(total_amount)),
            ('main_net', bucket / 50000.0 * float(total_amount)),
            ('main_ratio', bucket / 500.0),
            ('main_buy_net', main_buy_bucket / 50000.0 * float(total_amount)),
            ('main_buy_ratio', main_buy_bucket / 500.0),
            ('main_super_large_net', (buckets[0] - buckets[1]) * scale),
            ('main_large_net', (buckets[4] - buckets[5]) * scale),
            ('main_medium_net', (buckets[8] - buckets[9]) * scale),
            ('main_small_net', (buckets[12] - buckets[13]) * scale),
            ('main_buy_super_large_net', (buckets[2] - buckets[3]) * scale),
            ('main_buy_large_net', (buckets[6] - buckets[7]) * scale),
            ('main_buy_medium_net', (buckets[10] - buckets[11]) * scale),
            ('main_buy_small_net', (buckets[14] - buckets[15]) * scale),
        ])
