# coding=utf-8
"""
批量行情快照接口 0x054c

参考实现: eltdx crates/eltdx-protocol/src/commands/quotes.rs
请求 data: prefix[8] + count_u16 + [market(1)+code(6)]...
响应: skip(2) + count_u16 + 变长记录(用 code 标记 market+code 切分)
返回现价、成交量额和一档盘口(买一/卖一), 比 0x053e 轻量
"""

from collections import OrderedDict
import struct

from pytdx.parser.base import BaseParser
from pytdx.helper import get_price, get_volume

TYPE_SNAPSHOTS = 0x054c
QUOTE_LIST_PREFIX = bytes([5, 0, 0, 0, 0, 0, 0, 0])


class GetSnapshotsCmd(BaseParser):
    """显式代码批量行情快照(轻量, 仅买一/卖一)"""

    def setParams(self, all_stock):
        """
        :param all_stock: [(market, code), ...] 如 [(0, '000001'), (1, '600000')]
        """
        stock_len = len(all_stock)
        if stock_len <= 0:
            return False
        data = bytearray(QUOTE_LIST_PREFIX)
        data += struct.pack('<H', stock_len)
        self._markers = []
        for stock in all_stock:
            market, code = stock
            if isinstance(code, str):
                code = code.encode('utf-8')
            data += struct.pack('<B6s', market, code)
            self._markers.append(bytes([market]) + code)
        length = len(data) + 2
        self.send_pkg = struct.pack('<BIBHHH', 0x0c, 0x01016408, 0x01,
                                    length, length, TYPE_SNAPSHOTS) + bytes(data)

    def parseResponse(self, body_buf):
        if len(body_buf) < 4:
            return []
        pos = 2  # skip first 2 bytes
        (count,) = struct.unpack('<H', body_buf[pos:pos + 2])
        pos += 2
        data = body_buf[pos:]
        # 用请求代码标记切分变长记录
        starts = []
        search_from = 0
        for i in range(min(count, len(self._markers))):
            marker = self._markers[i]
            idx = data.find(marker, search_from)
            if idx < 0:
                break
            starts.append(idx)
            search_from = idx + len(marker)
        results = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(data)
            rec = data[start:end]
            results.append(self._parse_record(rec))
        return results

    def _parse_record(self, rec):
        if len(rec) < 9:
            return OrderedDict()
        market = rec[0]
        code = rec[1:7].decode('utf-8', errors='replace')
        (active1,) = struct.unpack('<H', rec[7:9])
        pos = 9
        price, pos = get_price(rec, pos)          # close (current)
        last_close_diff, pos = get_price(rec, pos)
        open_diff, pos = get_price(rec, pos)
        high_diff, pos = get_price(rec, pos)
        low_diff, pos = get_price(rec, pos)
        servertime, pos = get_price(rec, pos)
        reversed1, pos = get_price(rec, pos)
        vol, pos = get_price(rec, pos)
        cur_vol, pos = get_price(rec, pos)
        (amount_raw,) = struct.unpack('<I', rec[pos:pos + 4])
        amount = get_volume(amount_raw)
        pos += 4
        s_vol, pos = get_price(rec, pos)
        b_vol, pos = get_price(rec, pos)
        reversed2, pos = get_price(rec, pos)
        open_amount, pos = get_price(rec, pos)
        bid1_diff, pos = get_price(rec, pos)
        ask1_diff, pos = get_price(rec, pos)
        bid_vol1, pos = get_price(rec, pos)
        ask_vol1, pos = get_price(rec, pos)
        return OrderedDict([
            ('market', market),
            ('code', code),
            ('active1', active1),
            ('price', self._cal(price, 0)),
            ('last_close', self._cal(price, last_close_diff)),
            ('open', self._cal(price, open_diff)),
            ('high', self._cal(price, high_diff)),
            ('low', self._cal(price, low_diff)),
            ('servertime', servertime),
            ('vol', vol),
            ('cur_vol', cur_vol),
            ('amount', amount),
            ('s_vol', s_vol),
            ('b_vol', b_vol),
            ('open_amount', open_amount),
            ('bid1', self._cal(price, bid1_diff)),
            ('ask1', self._cal(price, ask1_diff)),
            ('bid_vol1', bid_vol1),
            ('ask_vol1', ask_vol1),
        ])

    def _cal(self, base_p, diff):
        return float(base_p + diff) / 100
