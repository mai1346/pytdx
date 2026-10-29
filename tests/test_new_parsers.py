#coding: utf-8
"""
新增 parser 的离线单元测试

测试数据来自 eltdx (electkismet/eltdx) Rust 实现中的冻结 wire-data,
可在无实盘服务器的条件下验证请求组包与响应解析的正确性。
"""
import struct

from pytdx.parser.get_call_auction import GetCallAuctionCmd
from pytdx.parser.get_special_limits import GetSpecialLimitsCmd
from pytdx.parser.get_delisted_bars import GetDelistedBarsCmd
from pytdx.parser.get_category_quotes import GetCategoryQuotesCmd
from pytdx.parser.get_snapshots import GetSnapshotsCmd
from pytdx.parser.get_money_flow import GetMoneyFlowCmd


# ---------- 集合竞价 0x056a ----------

def test_call_auction_request_wire():
    """请求包 data 区与 eltdx 冻结数据对齐 (sz000988, selector=3, limit=500)"""
    cmd = GetCallAuctionCmd(None)
    cmd.setParams(0, '000988', date=0, selector=3, start=0, limit=500)
    # 跳过 12 字节帧头, 校验 data 区
    data = cmd.send_pkg[12:]
    expected = bytes([0, 0]) + b'000988' + struct.pack('<IIIII', 0, 3, 0, 0, 500)
    assert data == expected, [hex(b) for b in data]


def test_call_auction_response_parse():
    """解析单条竞价记录, 时间 09:15:00, 撮合量 2568, 未匹配 2433"""
    payload = bytes([1, 0, 0x2b, 0x02, 0xb8, 0x1e, 0x22, 0x43,
                     0x08, 0x0a, 0x00, 0x00, 0x81, 0x09, 0x00, 0x00, 0x00, 0x00])
    cmd = GetCallAuctionCmd(None)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r['time'] == '09:15:00'
    assert r['matched_volume'] == 2568
    assert r['unmatched_volume'] == 2433
    assert r['unmatched_direction'] == 1


def test_call_auction_request_with_date():
    """历史日期 sh600519 20260807"""
    cmd = GetCallAuctionCmd(None)
    cmd.setParams(1, '600519', date=20260807)
    data = cmd.send_pkg[12:]
    assert data[8:12] == struct.pack('<I', 20260807)


# ---------- 特殊品种涨跌停 0x0452 ----------

def test_special_limits_request_wire():
    """请求包 data 区: start(2) + 12字节0"""
    cmd = GetSpecialLimitsCmd(None)
    cmd.setParams(start=2)
    data = cmd.send_pkg[12:]
    assert data[:2] == bytes([2, 0])
    assert len(data) == 14
    assert all(b == 0 for b in data[2:])


def test_special_limits_response_parse():
    """解析单条记录: code=123054, upper=212.531, lower=141.687"""
    payload = bytes([1, 0, 0]) + struct.pack('<I', 123054) + \
        struct.pack('<f', 212.531) + struct.pack('<f', 141.687)
    cmd = GetSpecialLimitsCmd(None)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r['code'] == '123054'
    assert abs(r['upper_limit'] - 212.531) < 0.001
    assert abs(r['lower_limit'] - 141.687) < 0.001


# ---------- 退市K线 0x052b ----------

def test_delisted_bars_request_wire():
    """请求包 data 区与 eltdx 冻结数据对齐 (sz000038, start=800, count=20)"""
    cmd = GetDelistedBarsCmd(None)
    cmd.setParams(0, '000038', start=800, count=20)
    data = cmd.send_pkg[12:]
    expected = struct.pack('<H6sHH', 0, b'000038', 800, 20)
    assert data == expected


def test_delisted_bars_response_parse():
    """解析单条日线: 收盘价 3.50, 成交量 4413700 股"""
    payload = bytes([1, 0, 0x18, 0xb1, 0x34, 0x01, 0xb8, 0x33, 0xb4, 0x02,
                     0x88, 0x03, 0x00, 0x84, 0xe4, 0x9a, 0x04, 0xdb, 0xb8,
                     0x67, 0x4b, 0, 0, 1, 0])
    cmd = GetDelistedBarsCmd(None)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    r = rows[0]
    assert abs(r['close'] - 3.5) < 0.001          # 3500 milli / 1000
    assert abs(r['vol'] - 44137.0) < 0.001        # 4413700 / 100 股


# ---------- 批量快照 0x054c ----------

def test_snapshots_request_wire():
    """请求包 data 区与 eltdx 冻结数据对齐"""
    cmd = GetSnapshotsCmd(None)
    cmd.setParams([(0, '000001'), (1, '600000'), (2, '899050')])
    data = cmd.send_pkg[12:]
    expected = bytes([5, 0, 0, 0, 0, 0, 0, 0, 3, 0,
                      0, *b'000001', 1, *b'600000', 2, *b'899050'])
    assert data == expected, [hex(b) for b in data]


# ---------- 分类行情 0x054b ----------

def test_category_quotes_request_wire():
    """请求包 data 区与 eltdx 冻结数据对齐 (沪深A股, count=42)"""
    cmd = GetCategoryQuotesCmd(None)
    cmd.setParams(6, start=0, count=42, sort_type=0, ascending=False, sort_reverse=0)
    data = cmd.send_pkg[12:]
    expected = struct.pack('<9H', 6, 0, 0, 42, 0, 5, 0, 1, 0)
    assert data == expected


def test_category_quotes_alias():
    """中文分类别名 '沪深a股' -> 6"""
    cmd = GetCategoryQuotesCmd(None)
    cmd.setParams('沪深a股', start=0, count=42, sort_type='涨幅')
    data = cmd.send_pkg[12:]
    assert data[:2] == struct.pack('<H', 6)           # category=6
    assert data[2:4] == struct.pack('<H', 0x000e)     # sort_type=涨幅=14


# ---------- 资金流向 0x0ffc ----------

def test_money_flow_request_wire():
    """请求包与 eltdx 冻结数据对齐 (sz000063), msg_id 编码路由"""
    cmd = GetMoneyFlowCmd(None)
    cmd.setParams(0, '000063')
    raw = cmd.send_pkg
    # 帧头: 0c 5e 2d 7e 00 01 28 00 28 00 fc 0f
    assert raw[:12] == bytes([0x0c, 0x5e, 0x2d, 0x7e, 0, 1, 0x28, 0, 0x28, 0, 0xfc, 0x0f])
    assert raw[12:20] == bytes([0, 0]) + b'000063'


def test_money_flow_response_parse():
    """解析 5 条记录, 主力净额 240, 主力占比 0.24 等 (eltdx 冻结数据)"""
    record_size = 0x58
    payload = bytearray(0x28 + 5 * record_size)
    payload[2:8] = b'000063'
    payload[0x26:0x28] = struct.pack('<H', 5)
    rec_off = 0x28
    payload[rec_off + 8:rec_off + 12] = struct.pack('<f', 100000.0)  # total_amount
    pairs = [(10, 100, 20), (11, 300, 100), (12, 50, 10), (13, 200, 100),
             (14, 60, 10), (15, 30, 10), (16, 20, 70), (17, 70, 20)]
    for index, lo, hi in pairs:
        packed = lo | (hi << 16)
        off = rec_off + 4 + index * 4
        payload[off:off + 4] = struct.pack('<I', packed)
    cmd = GetMoneyFlowCmd(None)
    rows = cmd.parseResponse(bytes(payload))
    assert len(rows) == 5
    r = rows[0]
    assert r['code'] == '000063'
    assert abs(r['main_net'] - 240.0) < 1e-6
    assert abs(r['main_ratio'] - 0.24) < 1e-6
    assert abs(r['main_buy_net'] - 740.0) < 1e-6
    assert abs(r['main_buy_ratio'] - 0.74) < 1e-6
    assert abs(r['main_buy_super_large_net'] - 400.0) < 1e-6
    assert abs(r['main_buy_large_net'] - 200.0) < 1e-6
    assert abs(r['main_buy_medium_net'] - 40.0) < 1e-6
    assert abs(r['main_buy_small_net'] - 100.0) < 1e-6
    assert abs(r['main_super_large_net'] - 160.0) < 1e-6
    assert abs(r['main_large_net'] - 80.0) < 1e-6
    assert abs(r['main_medium_net'] - 100.0) < 1e-6
    assert abs(r['main_small_net'] - (-100.0)) < 1e-6
