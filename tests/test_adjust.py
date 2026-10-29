#coding: utf-8
"""复权(前复权/后复权)模块单元测试"""
from pytdx.adjust import qfq, hfq, get_factors


def _xdxr(date, category=1, fenhong=0, songzhuangu=0, peigu=0, peigujia=0, suogu=0):
    y, m, d = date
    return {'year': y, 'month': m, 'day': d, 'category': category,
            'fenhong': fenhong, 'songzhuangu': songzhuangu,
            'peigu': peigu, 'peigujia': peigujia, 'suogu': suogu}


def _bar(date, close, open_=None, high=None, low=None):
    y, m, d = date
    return {'year': y, 'month': m, 'day': d,
            'open': open_ if open_ is not None else close,
            'close': close,
            'high': high if high is not None else close,
            'low': low if low is not None else close}


def test_qfq_single_songzhuangu():
    """10送5: 历史价 10 -> 6.67, 最新价不变"""
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5)]
    bars = [_bar((2024, 6, 9), 10.0), _bar((2024, 6, 10), 6.67)]
    out = qfq(bars, events)
    assert abs(out[0]['close'] - round(10.0 / 1.5, 2)) < 0.001  # 6.67
    assert abs(out[1]['close'] - 6.67) < 0.001                  # 最新不变


def test_qfq_single_dividend():
    """每股派0.5元: 历史价 10 -> 9.5"""
    events = [_xdxr((2024, 6, 10), fenhong=0.5)]
    bars = [_bar((2024, 6, 9), 10.0), _bar((2024, 6, 10), 9.5)]
    out = qfq(bars, events)
    assert abs(out[0]['close'] - 9.5) < 0.001
    assert abs(out[1]['close'] - 9.5) < 0.001


def test_hfq_single_songzhuangu():
    """10送5 后复权: 最新价 6.67 -> 10.01 (6.67*1.5=10.005 四舍五入向上)"""
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5)]
    bars = [_bar((2024, 6, 9), 10.0), _bar((2024, 6, 10), 6.67)]
    out = hfq(bars, events)
    assert abs(out[0]['close'] - 10.0) < 0.001  # 最早不变
    assert abs(out[1]['close'] - 10.01) < 0.001  # 6.67*1.5=10.005 四舍五入


def test_qfq_cumulative_two_events():
    """两次事件累积: 10送5 + 派0.5, 历史价 10 -> 6.17"""
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5),
              _xdxr((2024, 12, 10), fenhong=0.5)]
    bars = [_bar((2024, 6, 9), 10.0)]          # 两次事件之前
    out = qfq(bars, events)
    # 10 -> /1.5 = 6.667 -> -0.5 = 6.167
    assert abs(out[0]['close'] - round(10.0 / 1.5 - 0.5, 2)) < 0.001


def test_hfq_cumulative_two_events():
    """两次事件后复权: 最新价 6.17 -> 10.0"""
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5),
              _xdxr((2024, 12, 10), fenhong=0.5)]
    bars = [_bar((2024, 6, 9), 10.0), _bar((2024, 12, 11), 6.17)]
    out = hfq(bars, events)
    # 最早不变; 最新 6.17 -> +0.5=6.67 -> *1.5=10.005 四舍五入=10.01
    assert abs(out[0]['close'] - 10.0) < 0.001
    assert abs(out[1]['close'] - 10.01) < 0.001


def test_qfq_no_events_unchanged():
    bars = [_bar((2024, 1, 1), 10.0)]
    out = qfq(bars, [])
    assert out[0]['close'] == 10.0


def test_get_factors_returns_list():
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5)]
    factors = get_factors(events, 'qfq')
    assert len(factors) == 1
    date, mul, add = factors[0]
    assert date == (2024, 6, 10)
    assert abs(mul - 1.0 / 1.5) < 1e-9
    assert add == 0.0


def test_qfq_volume_not_adjusted():
    """成交量/额不复权"""
    events = [_xdxr((2024, 6, 10), songzhuangu=0.5)]
    bars = [_bar((2024, 6, 9), 10.0)]
    bars[0]['vol'] = 1000
    bars[0]['amount'] = 10000.0
    out = qfq(bars, events)
    assert out[0]['vol'] == 1000
    assert out[0]['amount'] == 10000.0
