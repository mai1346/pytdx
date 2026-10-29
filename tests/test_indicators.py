#coding: utf-8
"""技术指标模块单元测试"""
from pytdx import indicators as ind


def _bars(closes, highs=None, lows=None, vols=None, amounts=None):
    bars = []
    for i, c in enumerate(closes):
        bars.append({'close': c, 'high': highs[i] if highs else c,
                     'low': lows[i] if lows else c,
                     'vol': vols[i] if vols else 1,
                     'amount': amounts[i] if amounts else c})
    return bars


def test_ma():
    bars = _bars([1, 2, 3, 4, 5])
    out = ind.ma(bars, 3)
    assert out[:2] == [None, None]
    assert out[2] == 2.0
    assert out[3] == 3.0
    assert out[4] == 4.0


def test_ema():
    bars = _bars([10, 20, 30])
    out = ind.ema(bars, 2)
    assert out[0] is None
    assert out[1] is not None
    assert out[2] is not None


def test_macd_lengths():
    bars = _bars(list(range(1, 40)))
    dif, dea, hist = ind.macd(bars)
    assert len(dif) == len(dea) == len(hist) == 39


def test_rsi_basic():
    # 持续上涨 => RSI 趋近 100
    bars = _bars([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    out = ind.rsi(bars, 14)
    assert out[14] == 100.0


def test_boll():
    bars = _bars([1, 2, 3, 4, 5])
    upper, mid, lower = ind.boll(bars, 3)
    assert upper[2] >= mid[2] >= lower[2]


def test_atr():
    bars = _bars([10, 12, 8, 11], highs=[10, 12, 8, 11], lows=[9, 10, 7, 10])
    out = ind.atr(bars, 2)
    assert out[2] is not None


def test_vwap():
    bars = _bars([10, 20], vols=[100, 200], amounts=[1000, 4000])
    out = ind.vwap(bars)
    # 第1根: 1000/100=10; 第2根: (1000+4000)/(100+200)=16.67
    assert abs(out[0] - 10.0) < 0.01
    assert abs(out[1] - 5000.0 / 300) < 0.01
