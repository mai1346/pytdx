# coding=utf-8
"""
集合竞价明细接口 0x056a

参考实现: eltdx crates/eltdx-protocol/src/commands/auctions.rs
请求 data(28字节): market(1) + 0x00(1) + code(6) + date(4) + selector(4) + 0(4) + start(4) + limit(4)
响应: count(2) + count * [minute_of_day(2) + price_f32(4) + matched_vol_u32(4)
        + unmatched_signed_i32(4) + reserved(1) + second(1)]  每条 16 字节
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser

TYPE_CALL_AUCTION = 0x056a
AUCTION_RECORD_SIZE = 16
DEFAULT_AUCTION_SELECTOR = 3
DEFAULT_AUCTION_START = 0
DEFAULT_AUCTION_LIMIT = 500


class GetCallAuctionCmd(BaseParser):
    """集合竞价过程快照, 当日(date=0)或历史(date=YYYYMMDD)"""

    def setParams(self, market, code, date=0, selector=DEFAULT_AUCTION_SELECTOR,
                  start=DEFAULT_AUCTION_START, limit=DEFAULT_AUCTION_LIMIT):
        if isinstance(code, str):
            code = code.encode('utf-8')
        data = struct.pack('<BB6sIIIII', market, 0, code, date, selector, 0, start, limit)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_CALL_AUCTION) + data

    def parseResponse(self, body_buf):
        if len(body_buf) < 2:
            return []
        (count,) = struct.unpack('<H', body_buf[:2])
        pos = 2
        rows = []
        for i in range(count):
            if pos + AUCTION_RECORD_SIZE > len(body_buf):
                break
            (minute_of_day,) = struct.unpack('<H', body_buf[pos:pos + 2])
            (price,) = struct.unpack('<f', body_buf[pos + 2:pos + 6])
            (matched_vol,) = struct.unpack('<I', body_buf[pos + 6:pos + 10])
            (unmatched_signed,) = struct.unpack('<i', body_buf[pos + 10:pos + 14])
            second = body_buf[pos + 15]
            pos += AUCTION_RECORD_SIZE
            hour = minute_of_day // 60
            minute = minute_of_day % 60
            rows.append(OrderedDict([
                ('index', i),
                ('hour', hour),
                ('minute', minute),
                ('second', second),
                ('time', '%02d:%02d:%02d' % (hour, minute, second)),
                ('price', price),
                ('matched_volume', matched_vol),
                ('unmatched_volume', abs(unmatched_signed)),
                ('unmatched_direction', 1 if unmatched_signed >= 0 else -1),
            ]))
        return rows
