#coding: utf-8
"""P2 批次新增 parser 的离线单元测试 (数据来自 eltdx 冻结 wire-data)"""
import struct

from pytdx.parser.get_history_ticks import GetHistoryTicksCmd
from pytdx.parser.get_security_list_ex import GetSecurityListExCmd
from pytdx.parser.get_intraday_aux import GetIntradayAuxCmd, KIND_BUY_SELL, KIND_VOLUME_COMPARE
from pytdx.parser.get_sparkline import GetSparklineCmd
from pytdx.parser.get_recent_intraday import GetRecentIntradayCmd, _date_ordinal


# ---------- 历史成交明细增强 0x0fc6 ----------

def test_history_ticks_request_wire():
    """请求包 data 与 eltdx 冻结数据对齐 (sz300308, date=20260511, count=900)"""
    cmd = GetHistoryTicksCmd(None)
    cmd.setParams(0, '300308', 20260511, start=0, count=900)
    data = cmd.send_pkg[12:]
    expected = bytes([0x9f, 0x26, 0x35, 0x01, 0, 0]) + b'300308' + struct.pack('<HH', 0, 900)
    assert data == expected


def test_history_ticks_response_parse():
    """解析单条: 14:08, price=0.10, status=5"""
    payload = bytes([1, 0]) + struct.pack('<f', 35.5) + bytes([0x50, 0x03, 0x0a, 0x14, 0x03, 0x05, 0x00])
    cmd = GetHistoryTicksCmd(None)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r['time'] == '14:08'
    assert abs(r['price'] - 0.1) < 0.001   # price_acc=10, /100
    assert r['vol'] == 20
    assert r['status'] == 5
    assert r['side'] == 'status_5'


# ---------- 代码表分页 0x044d ----------

def test_security_list_ex_request_wire():
    """请求包 data 与 eltdx 冻结数据对齐 (Beijing, limit=1600)"""
    cmd = GetSecurityListExCmd(None)
    cmd.setParams(2, start=0, limit=1600)
    data = cmd.send_pkg[12:]
    expected = bytes([2, 0, 0, 0, 0, 0, 0x40, 0x06, 0, 0, 0, 0, 0, 0])
    assert data == expected


def test_security_list_ex_response_parse():
    """解析单条: sz000001 平安银行"""
    record = bytearray(b'000001')
    record += struct.pack('<H', 100)                              # multiple
    record += b'\xc6\xbd\xb0\xb2\xd2\xf8\xd0\xd0' + b'\x00' * 8  # name GBK "平安银行"
    record += struct.pack('<f', 3956.6565)                        # unknown0
    record += bytes([2])                                          # decimal
    record += struct.pack('<f', 10.99)                            # prev_close
    record += bytes([0x67, 0x31, 0x68, 0x25])                     # unknown3
    payload = struct.pack('<H', 1) + bytes(record)
    cmd = GetSecurityListExCmd(None)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r['code'] == '000001'
    assert r['name'] == '平安银行'
    assert r['decimal'] == 2
    assert abs(r['prev_close'] - 10.99) < 0.001


# ---------- 分时副图 0x051b ----------

def test_intraday_aux_request_wire():
    """请求包长度 28, 末字节 kind=0x0b"""
    cmd = GetIntradayAuxCmd(None)
    cmd.setParams(0, '000988', kind=KIND_VOLUME_COMPARE)
    data = cmd.send_pkg[12:]
    assert len(data) == 28
    assert data[27] == 0x0b


def test_intraday_aux_buy_sell_response():
    """买卖力道: count=1, series_a=5, series_b=6"""
    cmd = GetIntradayAuxCmd(None)
    cmd.setParams(0, '000988', kind=KIND_BUY_SELL)
    rows = cmd.parseResponse(bytes([1, 0, 5, 6]))
    assert len(rows) == 1
    assert rows[0]['buy_strength'] == 5
    assert rows[0]['sell_strength'] == 6
    assert rows[0]['time'] == '09:31'


def test_intraday_aux_volume_response():
    """成交对比: count=1, prev=100.5, curr=120.5"""
    payload = bytes([1, 0]) + struct.pack('<f', 100.5) + struct.pack('<f', 120.5)
    cmd = GetIntradayAuxCmd(None)
    cmd.setParams(0, '000988', kind=KIND_VOLUME_COMPARE)
    rows = cmd.parseResponse(payload)
    assert len(rows) == 1
    assert abs(rows[0]['prev_day_vol'] - 100.5) < 0.001
    assert abs(rows[0]['curr_day_vol'] - 120.5) < 0.001


# ---------- 小走势图 0x0fd1 ----------

def test_sparkline_request_wire():
    """请求包长度 37, selector=1, window=20, fixed=0x01000000"""
    cmd = GetSparklineCmd(None)
    cmd.setParams(0, '000001', selector=1, window=20)
    data = cmd.send_pkg[12:]
    assert len(data) == 37
    assert data[24:32] == bytes([1, 0, 20, 0, 0, 0, 0, 1])


def test_sparkline_response_parse():
    """解析: code=000001, max_count=60, prices=[10.0, 10.1]"""
    payload = bytearray([0, 0]) + b'000001' + b'\x00' * 16
    payload += bytes([1, 0]) + struct.pack('<I', 0) + struct.pack('<I', 0)
    payload += struct.pack('<H', 60) + struct.pack('<f', 10.0) + struct.pack('<H', 2)
    payload += struct.pack('<f', 10.0) + struct.pack('<f', 10.1)
    cmd = GetSparklineCmd(None)
    r = cmd.parseResponse(bytes(payload))
    assert r['code'] == '000001'
    assert r['max_count'] == 60
    assert len(r['prices']) == 2
    assert abs(r['prices'][1] - 10.1) < 0.001


# ---------- 近期历史分时 0x0feb ----------

def test_date_ordinal():
    """eltdx python_date_ordinal(2026,5,11) = 739747"""
    assert _date_ordinal(2026, 5, 11) == 739747


def test_recent_intraday_request_wire():
    """请求包 data 与 eltdx 冻结数据对齐 (sz300308, 20260511)"""
    cmd = GetRecentIntradayCmd(None)
    cmd.setParams(0, '300308', 20260511)
    data = cmd.send_pkg[12:]
    # selector = 0xfed62304 - 739747 = 0xfecad961, LE = 61 d9 ca fe
    assert data[:4] == bytes([0x61, 0xd9, 0xca, 0xfe])
    assert data[4:] == bytes([0]) + b'300308'


def test_recent_intraday_response_parse():
    """解析单条分时点"""
    payload = bytes([1, 0]) + struct.pack('<f', 10.0) + struct.pack('<f', 10.1) + bytes([10, 11, 12])
    cmd = GetRecentIntradayCmd(None)
    result = cmd.parseResponse(payload)
    assert abs(result['prev_close'] - 10.0) < 0.001
    assert len(result['points']) == 1
    assert abs(result['points'][0]['price'] - 0.01) < 0.001  # 10/1000
