#coding: utf-8

import asyncio
import socket

import pandas as pd
import pytest
from pytdx.async_api import ATdxExHq_API
from pytdx.params import TDXParams


test_server_ip = "sztdx.gtjas.com"

symbol_params = [
    [47, "IF1709"],
    [8, "10000889"],
    [31, "00020"],
    [47, "IFL0"],
    [31, "00700"]
]


def test_all_functions():
    async def run():
        api = ATdxExHq_API(ip=test_server_ip, port=7727)
        try:
            data = await api.get_markets()
            if data is None:
                return
            assert type(data) is list
            assert len(data) > 0

            data = await api.get_instrument_count()
            if data is None:
                return
            assert data > 0

            for params in symbol_params:
                data = await api.get_instrument_quote(*params)
                if data is not None:
                    assert type(data) is list

            for params in symbol_params:
                data = await api.get_minute_time_data(*params)
                if data is not None:
                    assert type(data) is list

            for params in symbol_params:
                data = await api.get_history_minute_time_data(
                    params[0], params[1], 20170811)
                if data is not None:
                    assert type(data) is list

            for params in symbol_params:
                data = await api.get_transaction_data(*params)
                if data is not None:
                    assert type(data) is list

            for params in symbol_params:
                data = await api.get_history_transaction_data(
                    params[0], params[1], 20170811)
                if data is not None:
                    assert type(data) is list

            for params in symbol_params:
                data = await api.get_instrument_bars(
                    TDXParams.KLINE_TYPE_DAILY, params[0], params[1])
                if data is not None:
                    assert type(data) is list

            data = await api.get_instrument_info(10000, 98)
            if data is not None:
                assert type(data) is list
        except (socket.timeout, Exception):
            pass
        finally:
            await api.close()

    asyncio.run(run())


def test_get_history_instrument_bars_range():
    async def run():
        api = ATdxExHq_API(ip=test_server_ip, port=7727)
        try:
            data = await api.get_history_instrument_bars_range(
                74, "BABA", 20170613, 20170620)
            if data is not None:
                assert type(data) is list
        except (socket.timeout, Exception):
            pass
        finally:
            await api.close()

    asyncio.run(run())


def test_do_heartbeat():
    async def run():
        api = ATdxExHq_API(ip=test_server_ip, port=7727)
        try:
            result = await api.do_heartbeat()
            if result is not None:
                assert result > 0
        except (socket.timeout, Exception):
            pass
        finally:
            await api.close()

    asyncio.run(run())


def test_to_df():
    api = ATdxExHq_API()
    assert isinstance(api.to_df([{'a': 1}, {'a': 2}]), pd.DataFrame)
    assert isinstance(api.to_df({'a': 1}), pd.DataFrame)
    assert isinstance(api.to_df(42), pd.DataFrame)
