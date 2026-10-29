# coding=utf-8

from pytdx.parser.base import BaseParser
from pytdx.helper import get_datetime, get_volume, get_price
from collections import OrderedDict
import struct

"""
param: category=9, market=1, stockcode=000001, start=0, count=10


In [101]: l[12:19]
Out[101]: bytearray(b'xD\x9eI\xbe\xf7\nR')

should be :

1296527
149215477760.00000


bytearray(b'\xa8\xa9\xa4I\x10R\rR') = 1348917 151741792256.00000

"""



class GetIndexBarsCmd(BaseParser):

    def setParams(self, category, market, code, start, count, adjust=0, anchor_date=0):
        """
        :param adjust: 复权模式 0=不复权 1=前复权 2=后复权 3=固定前复权 4=固定后复权
        :param anchor_date: 复权锚点日期 YYYYMMDD, 0 表示以最新交易日为锚 (仅 adjust>=3 时生效)
        """
        if type(code) is str:
            code = code.encode("utf-8")

        self.category = category

        # 42 字节新协议布局 (eltdx 2026):
        # market(2) + code(6) + period.raw(2) + period.parameter(2)
        # + start(2) + count(2) + adjust(2) + anchor_date(4) + 20字节0
        values = (
            0x10c,         # H magic1
            0x01016408,    # I magic2
            0x2a,          # H pkgdatalen = 42
            0x2a,          # H pkgdatalen = 42
            0x052d,        # H type
            market,        # H market
            code,          # 6s code
            category,      # H period.raw
            1,             # H period.parameter
            start,         # H start
            count,         # H count
            adjust,        # H adjust (新增)
            anchor_date,   # I anchor_date (新增)
        )

        pkg = struct.pack("<HIHHHH6sHHHHHI", *values) + b'\x00' * 20
        self.send_pkg = pkg

    def parseResponse(self, body_buf):
        pos = 0

        (ret_count,) = struct.unpack("<H", body_buf[0: 2])
        pos += 2

        klines = []

        pre_diff_base = 0
        for i in range(ret_count):
            year, month, day, hour, minute, pos = get_datetime(self.category, body_buf, pos)

            price_open_diff, pos = get_price(body_buf, pos)
            price_close_diff, pos = get_price(body_buf, pos)

            price_high_diff, pos = get_price(body_buf, pos)
            price_low_diff, pos = get_price(body_buf, pos)

            (vol_raw,) = struct.unpack("<I", body_buf[pos: pos + 4])
            vol = get_volume(vol_raw)

            pos += 4
            (dbvol_raw,) = struct.unpack("<I", body_buf[pos: pos + 4])
            dbvol = get_volume(dbvol_raw)
            pos += 4

            (up_count, down_count) = struct.unpack("<HH", body_buf[pos: pos + 4])
            pos += 4

            open = self._cal_price1000(price_open_diff, pre_diff_base)

            price_open_diff = price_open_diff + pre_diff_base

            close = self._cal_price1000(price_open_diff, price_close_diff)
            high = self._cal_price1000(price_open_diff, price_high_diff)
            low = self._cal_price1000(price_open_diff, price_low_diff)

            pre_diff_base = price_open_diff + price_close_diff

            #### 为了避免python处理浮点数的时候，浮点数运算不精确问题，这里引入了多余的代码

            kline = OrderedDict([
                ("open", open),
                ("close", close),
                ("high", high),
                ("low", low),
                ("vol", vol),
                ("amount", dbvol),
                ("year", year),
                ("month", month),
                ("day", day),
                ("hour", hour),
                ("minute", minute),
                ("datetime", "%d-%02d-%02d %02d:%02d" % (year, month, day, hour, minute)),
                ("up_count", up_count),
                ("down_count", down_count)
            ])
            klines.append(kline)
        return klines

    def _cal_price1000(self, base_p, diff):
        return float(base_p + diff)/1000