# coding=utf-8

from pytdx.parser.base import BaseParser
from pytdx.helper import get_volume
from collections import OrderedDict
import struct


class GetSecurityIndexList(BaseParser):

    def setParams(self, market, start):
        pkg = bytearray.fromhex('0c 01 18 6b 01 01 06 00 06 00 50 04')
        pkg_param = struct.pack("<HH", market, start)
        pkg.extend(pkg_param)
        self.send_pkg = pkg

    def parseResponse(self, body_buf):

        pos = 0
        (num, ) = struct.unpack("<H", body_buf[:2])
        pos += 2
        stocks = []
        for i in range(num):

            one_bytes = body_buf[pos: pos + 29]

            (code, volunit,
             name_bytes, reversed_bytes1, decimal_point,
             pre_close_raw, reversed_bytes2) = struct.unpack("<6sH8s4sBI4s", one_bytes)

            code = code.decode("utf-8")
            name = name_bytes.decode("gbk", errors="replace").rstrip("\x00")
            pre_close = get_volume(pre_close_raw)
            pos += 29

            one = OrderedDict(
                [
                    ('code', code),
                    ('volunit', volunit),
                    ('decimal_point', decimal_point),
                    ('name', name),
                    ('pre_close', pre_close),
                ]
            )

            stocks.append(one)


        return stocks
