#coding: utf-8
"""
0x052d K线新协议 (42字节布局) 请求包验证

测试数据来自 eltdx (electkismet/eltdx) Rust 实现中的冻结 wire-data,
验证请求包字节布局与 eltdx klines.rs 的 KlinesRequest::frame() 逐字节对齐。

参考: eltdx crates/eltdx-protocol/src/commands/klines.rs
  fn kline_request_matches_frozen_day_wire_data:
    code = sz300308, period = day, start = 0, count = 420, adjust = None, anchor_date = 0
    assert_eq!(frame.data.len(), 42);
    assert_eq!(&frame.data[8..12], &[4, 0, 1, 0]);       // period.raw=4, parameter=1
    assert_eq!(&frame.data[12..16], &[0, 0, 0xa4, 0x01]); // start=0, count=420=0x01a4
"""
import struct

from pytdx.parser.get_security_bars import GetSecurityBarsCmd
from pytdx.parser.get_index_bars import GetIndexBarsCmd


def _data_area(cmd):
    """返回请求包的 data 区 (跳过 12 字节帧头)"""
    return cmd.send_pkg[12:]


def _header(cmd):
    """返回 (magic1, magic2, pkgdatalen1, pkgdatalen2, type)"""
    return struct.unpack('<HIHHH', cmd.send_pkg[:12])


# ---------- 请求包结构验证 ----------

def test_security_bars_total_length():
    """请求包总长 = 12(帧头) + 42(data) = 54 字节"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10)
    assert len(cmd.send_pkg) == 54


def test_security_bars_pkgdatalen_is_42():
    """pkgdatalen 标记应为 42 (0x2a), 修复旧版标记 28 但实际 26 的不一致"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10)
    magic1, magic2, len1, len2, typ = _header(cmd)
    assert magic1 == 0x10c
    assert magic2 == 0x01016408
    assert len1 == 0x2a  # 42
    assert len2 == 0x2a  # 42
    assert typ == 0x052d


def test_security_bars_data_length_is_42():
    """data 区长度 = 42 字节"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10)
    assert len(_data_area(cmd)) == 42


# ---------- 与 eltdx 冻结数据对齐 ----------

def test_security_bars_matches_eltdx_frozen_wire():
    """
    与 eltdx klines.rs 冻结测试数据对齐:
      sz300308, day(period.raw=4, parameter=1), start=0, count=420, adjust=None, anchor_date=0
      eltdx 断言: data.len()==42, data[8:12]==[4,0,1,0], data[12:16]==[0,0,0xa4,0x01]
    """
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(category=4, market=0, code='300308', start=0, count=420,
                  adjust=0, anchor_date=0)
    data = _data_area(cmd)
    assert len(data) == 42
    assert data[0:2] == struct.pack('<H', 0)          # market=0 (sz)
    assert data[2:8] == b'300308'                     # code
    assert data[8:10] == struct.pack('<H', 4)         # period.raw=4 (day)
    assert data[10:12] == struct.pack('<H', 1)        # period.parameter=1
    assert data[12:14] == struct.pack('<H', 0)        # start=0
    assert data[14:16] == struct.pack('<H', 420)      # count=420 (0x01a4)
    # eltdx 冻结断言
    assert data[8:12] == bytes([4, 0, 1, 0])
    assert data[12:16] == bytes([0, 0, 0xa4, 0x01])


def test_security_bars_adjust_and_anchor_date_fields():
    """验证 adjust (data[16:18]) 和 anchor_date (data[18:22]) 字段位置"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10, adjust=1, anchor_date=20260101)
    data = _data_area(cmd)
    assert data[16:18] == struct.pack('<H', 1)              # adjust=1 (前复权)
    assert data[18:22] == struct.pack('<I', 20260101)       # anchor_date


def test_security_bars_trailing_20_zeros():
    """data[22:42] = 20 字节零 (扩展保留区)"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10)
    data = _data_area(cmd)
    assert data[22:42] == b'\x00' * 20


def test_security_bars_default_adjust_is_zero():
    """默认 adjust=0, anchor_date=0 (向后兼容, 不复权)"""
    cmd = GetSecurityBarsCmd(None)
    cmd.setParams(4, 0, '000001', 0, 10)
    data = _data_area(cmd)
    assert data[16:18] == b'\x00\x00'   # adjust=0
    assert data[18:22] == b'\x00\x00\x00\x00'  # anchor_date=0


# ---------- index_bars 同样验证 ----------

def test_index_bars_total_length():
    """指数K线请求包同样升级到 54 字节"""
    cmd = GetIndexBarsCmd(None)
    cmd.setParams(9, 1, '000001', 0, 10)
    assert len(cmd.send_pkg) == 54


def test_index_bars_pkgdatalen_is_42():
    cmd = GetIndexBarsCmd(None)
    cmd.setParams(9, 1, '000001', 0, 10)
    _, _, len1, len2, typ = _header(cmd)
    assert len1 == 0x2a
    assert len2 == 0x2a
    assert typ == 0x052d


def test_index_bars_matches_eltdx_frozen_wire():
    """指数K线请求与 eltdx 同布局 (sh000001, day)"""
    cmd = GetIndexBarsCmd(None)
    cmd.setParams(category=4, market=1, code='000001', start=0, count=420,
                  adjust=0, anchor_date=0)
    data = _data_area(cmd)
    assert len(data) == 42
    assert data[0:2] == struct.pack('<H', 1)          # market=1 (sh)
    assert data[2:8] == b'000001'
    assert data[8:12] == bytes([4, 0, 1, 0])          # period.raw=4, parameter=1
    assert data[12:16] == bytes([0, 0, 0xa4, 0x01])   # start=0, count=420


def test_index_bars_adjust_field():
    """指数K线也支持 adjust/anchor_date"""
    cmd = GetIndexBarsCmd(None)
    cmd.setParams(4, 1, '000001', 0, 10, adjust=2, anchor_date=0)
    data = _data_area(cmd)
    assert data[16:18] == struct.pack('<H', 2)   # adjust=2 (后复权)


# ---------- 向后兼容性验证 ----------

def test_backward_compatible_default_call():
    """旧调用方式 setParams(category, market, code, start, count) 仍可用"""
    cmd = GetSecurityBarsCmd(None)
    # 不传 adjust/anchor_date, 使用默认值
    cmd.setParams(4, 0, '000001', 0, 10)
    assert len(cmd.send_pkg) == 54
    data = _data_area(cmd)
    # adjust 和 anchor_date 默认为 0
    assert data[16:22] == b'\x00' * 6
