# coding=utf-8
"""
前复权 / 后复权 (QFQ / HFQ) 本地计算

基于除权除息(gbbq/xdxr)事件做仿射变换: price_adj = mul * price_raw + add
结果四舍五入到分(2位小数), 对齐通达信桌面端口径

数据来源: pytdx 的 get_xdxr_info / get_xdxr_info 返回的 category=1 (除权除息) 事件
  - fenhong    每股派息(元)
  - songzhuangu 送转股率 (0.5 = 10送5)
  - peigu      配股率
  - peigujia   配股价(元)

公式 (单次除权除息):
  除权参考价 = (前收 - fenhong + peigu*peigujia) / (1 + songzhuangu + peigu)
  前复权: P_qfq = (P - fenhong + peigu*peigujia) / (1 + songzhuangu + peigu)
          => mul = 1/(1+s+r), add = (peigu*peigujia - fenhong)/(1+s+r)
  后复权: P_hfq = P * (1 + songzhuangu + peigu) + (fenhong - peigu*peigujia)
          => mul = (1+s+r),    add = (fenhong - peigu*peigujia)

注意: 本地复权与服务端复权(0x052d adjust参数)在累计精度和舍入顺序上可能存在
      约 0.01~0.02 元差异, 需要服务端口径时请直接用服务端复权。
"""

from collections import OrderedDict


def _event_date(row):
    return (row.get('year', 0), row.get('month', 0), row.get('day', 0))


def _kline_date(kline):
    return (kline.get('year', 0), kline.get('month', 0), kline.get('day', 0))


def _compute_qfq_factor(row):
    """单条事件的 QFQ 仿射系数 (mul, add), 不适用返回 None"""
    category = row.get('category')
    if category == 1:
        fenhong = row.get('fenhong') or 0.0
        songzhuangu = row.get('songzhuangu') or 0.0
        peigu = row.get('peigu') or 0.0
        peigujia = row.get('peigujia') or 0.0
        denom = 1.0 + songzhuangu + peigu
        if denom == 0:
            return None
        mul = 1.0 / denom
        add = (peigu * peigujia - fenhong) / denom
        if mul == 1.0 and add == 0.0:
            return None
        return (mul, add)
    if category in (11, 12):  # 扩缩股 / 非流通股缩股
        suogu = row.get('suogu') or 0.0
        if suogu == 0 or suogu == 1:
            return None
        return (suogu, 0.0)
    return None


def _compute_hfq_factor(row):
    """单条事件的 HFQ 仿射系数 (mul, add)"""
    f = _compute_qfq_factor(row)
    if f is None:
        return None
    mul, add = f
    if mul == 0:
        return None
    # 逆: P = (P_qfq - add) / mul => P_hfq = P_qfq * (1/mul) + (-add/mul)
    return (1.0 / mul, -add / mul)


def _build_qfq_factors(xdxr_rows):
    """按日期排序的 (date, cum_mul, cum_add) 列表, cum 因子适用于该事件日期之前的 K 线"""
    events = []
    for row in xdxr_rows:
        f = _compute_qfq_factor(row)
        if f:
            events.append((_event_date(row), f[0], f[1]))
    events.sort(key=lambda x: x[0])
    # 从最新到最旧累积: factor_before_e_i = compose(e_i, factor_before_e_{i+1})
    factors = []
    cum_mul, cum_add = 1.0, 0.0
    for date, mul, add in reversed(events):
        new_mul = mul * cum_mul
        new_add = add * cum_mul + cum_add
        factors.append((date, new_mul, new_add))
        cum_mul, cum_add = new_mul, new_add
    factors.reverse()
    return factors


def _build_hfq_factors(xdxr_rows):
    """按日期排序的 (date, cum_mul, cum_add) 列表, cum 因子适用于该事件日期及之后的 K 线"""
    events = []
    for row in xdxr_rows:
        f = _compute_hfq_factor(row)
        if f:
            events.append((_event_date(row), f[0], f[1]))
    events.sort(key=lambda x: x[0])
    # 从最旧到最新累积: factor_after_e_i = compose(e_i, factor_after_e_{i-1})
    factors = []
    cum_mul, cum_add = 1.0, 0.0
    for date, mul, add in events:
        new_mul = mul * cum_mul
        new_add = add * cum_mul + cum_add
        factors.append((date, new_mul, new_add))
        cum_mul, cum_add = new_mul, new_add
    return factors


def _round2(x):
    """四舍五入到分(2位小数), 对齐通达信"""
    return round(x + 1e-9, 2)


def _adjust_price(p, mul, add):
    if p is None:
        return None
    return _round2(p * mul + add)


def _adjust_kline(kline, mul, add):
    """对单根 K 线的 OHLC 施加仿射变换, 成交量/额不复权"""
    if mul == 1.0 and add == 0.0:
        return kline
    out = OrderedDict(kline)
    for field in ('open', 'close', 'high', 'low'):
        if field in out and out[field] is not None:
            out[field] = _adjust_price(out[field], mul, add)
    return out


def get_factors(xdxr_rows, mode='qfq'):
    """获取复权因子列表 [(date, mul, add), ...] 供自行施加"""
    if mode in ('qfq', 'front'):
        return _build_qfq_factors(xdxr_rows)
    elif mode in ('hfq', 'back'):
        return _build_hfq_factors(xdxr_rows)
    raise ValueError("mode must be 'qfq' or 'hfq'")


def adjust(klines, xdxr_rows, mode='qfq'):
    """
    对 K 线列表做复权

    :param klines: list of dict, 每根含 open/close/high/low 及 year/month/day
    :param xdxr_rows: get_xdxr_info 返回的事件列表
    :param mode: 'qfq'(前复权) / 'hfq'(后复权)
    :return: 复权后的 K 线列表 (新 list, 不修改输入)
    """
    if mode in ('qfq', 'front'):
        factors = _build_qfq_factors(xdxr_rows)
        result = []
        for k in klines:
            dk = _kline_date(k)
            mul, add = 1.0, 0.0
            for fdate, fmul, fadd in factors:  # 已按日期升序
                if dk < fdate:  # K 线在该事件之前 => 需要调整
                    mul, add = fmul, fadd
                    break
            result.append(_adjust_kline(k, mul, add))
        return result
    elif mode in ('hfq', 'back'):
        factors = _build_hfq_factors(xdxr_rows)
        result = []
        for k in klines:
            dk = _kline_date(k)
            mul, add = 1.0, 0.0
            # 找最新的已发生事件 (date <= dk)
            for fdate, fmul, fadd in factors:  # 升序
                if dk >= fdate:
                    mul, add = fmul, fadd
                else:
                    break
            result.append(_adjust_kline(k, mul, add))
        return result
    raise ValueError("mode must be 'qfq' or 'hfq'")


def qfq(klines, xdxr_rows):
    """前复权 (最新价为锚, 历史价向下调整)"""
    return adjust(klines, xdxr_rows, 'qfq')


def hfq(klines, xdxr_rows):
    """后复权 (最早价为锚, 后续价向上调整)"""
    return adjust(klines, xdxr_rows, 'hfq')
