# coding=utf-8
"""
常用技术指标计算 (基于 K 线列表)

参考 injoyai/tdx protocol/model_kline.go 的指标实现。
输入: pytdx 各 get_*_bars 返回的 K 线 dict 列表, 含 close/high/low/vol/amount。
输出: 与输入等长的列表, 不足计算周期的位置为 None。
"""

import math


def _closes(klines):
    return [k.get('close', 0) for k in klines]


def ma(klines, n=20):
    """简单移动平均"""
    closes = _closes(klines)
    out = [None] * len(klines)
    for i in range(len(klines)):
        if i + 1 < n:
            continue
        out[i] = sum(closes[i + 1 - n:i + 1]) / n
    return out


def ema(klines, n=12):
    """指数移动平均"""
    closes = _closes(klines)
    if not closes:
        return []
    out = [None] * len(klines)
    out[0] = closes[0]
    k = 2.0 / (n + 1)
    for i in range(1, len(closes)):
        out[i] = closes[i] * k + out[i - 1] * (1 - k)
    if len(out) > 0:
        out[0] = None  # 第一根无前置, 置空
    return out


def macd(klines, fast=12, slow=26, signal=9):
    """MACD, 返回 (dif, dea, hist) 三个等长列表"""
    closes = _closes(klines)
    if not closes:
        return [], [], []
    ef = ema(klines, fast)
    es = ema(klines, slow)
    dif = [None] * len(closes)
    for i in range(len(closes)):
        if ef[i] is not None and es[i] is not None:
            dif[i] = ef[i] - es[i]
    # dea = EMA(dif, signal), 从第一个非 None 开始
    dea = [None] * len(closes)
    start = next((i for i, v in enumerate(dif) if v is not None), None)
    if start is not None:
        dea[start] = dif[start]
        k = 2.0 / (signal + 1)
        for i in range(start + 1, len(closes)):
            dea[i] = dif[i] * k + dea[i - 1] * (1 - k)
    hist = [None] * len(closes)
    for i in range(len(closes)):
        if dif[i] is not None and dea[i] is not None:
            hist[i] = (dif[i] - dea[i]) * 2
    return dif, dea, hist


def rsi(klines, n=14):
    """相对强弱指标"""
    closes = _closes(klines)
    out = [None] * len(closes)
    if len(closes) < n + 1:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, n + 1):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    out[n] = 100 * gains / (gains + losses) if (gains + losses) > 0 else 0
    for i in range(n + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        prev = closes[i - n] - closes[i - n - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
        if prev > 0:
            gains -= prev
        else:
            losses += prev
        out[i] = 100 * gains / (gains + losses) if (gains + losses) > 0 else 0
    return out


def boll(klines, n=20):
    """布林带, 返回 (upper, mid, lower)"""
    closes = _closes(klines)
    upper = [None] * len(klines)
    mid = [None] * len(klines)
    lower = [None] * len(klines)
    for i in range(n - 1, len(klines)):
        window = closes[i + 1 - n:i + 1]
        m = sum(window) / n
        var = sum((x - m) ** 2 for x in window) / n
        std = math.sqrt(var)
        mid[i] = m
        upper[i] = m + 2 * std
        lower[i] = m - 2 * std
    return upper, mid, lower


def atr(klines, n=14):
    """平均真实波幅"""
    if len(klines) < 2:
        return [None] * len(klines)
    trs = [0.0] * len(klines)
    for i in range(1, len(klines)):
        h = klines[i].get('high', 0)
        l = klines[i].get('low', 0)
        pc = klines[i - 1].get('close', 0)
        trs[i] = max(h - l, abs(h - pc), abs(l - pc))
    out = [None] * len(klines)
    if len(klines) <= n:
        return out
    s = sum(trs[1:n + 1])
    out[n] = s / n
    for i in range(n + 1, len(klines)):
        out[i] = (out[i - 1] * (n - 1) + trs[i]) / n
    return out


def vwap(klines):
    """成交量加权平均价 (全程)"""
    out = [None] * len(klines)
    vol_sum = 0.0
    amt_sum = 0.0
    for i, k in enumerate(klines):
        vol = k.get('vol', 0) or 0
        amt = k.get('amount', 0) or 0
        vol_sum += vol
        amt_sum += amt
        out[i] = amt_sum / vol_sum if vol_sum > 0 else None
    return out
