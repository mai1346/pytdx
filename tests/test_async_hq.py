#coding: utf-8

import asyncio
from collections import OrderedDict

import pandas as pd
import pytest
from pytdx.errors import TdxFunctionCallError
from pytdx.async_api import ATdxHq_API
from pytdx.params import TDXParams


test_server_ip = "sztdx.gtjas.com"


def test_all_functions():
    async def run():
        api = ATdxHq_API(ip=test_server_ip, raise_exception=True)
        try:
            stocks = await api.get_security_quotes([(0, "000001"), (1, "600300")])
            assert stocks is not None
            assert type(stocks) is list

            stocks = await api.get_security_quotes(0, "000001")
            assert stocks is not None
            assert type(stocks) is list

            stocks = await api.get_security_quotes((0, "000001"))
            assert stocks is not None
            assert type(stocks) is list

            data = await api.get_security_bars(9, 0, '000001', 4, 3)
            assert data is not None
            assert type(data) is list
            assert len(data) == 3

            assert await api.get_security_count(0) > 0

            stocks = await api.get_security_list(1, 0)
            assert stocks is not None
            assert type(stocks) is list
            assert len(stocks) > 0

            data = await api.get_index_bars(9, 1, '000001', 1, 2)
            assert data is not None
            assert type(data) is list
            assert len(data) == 2

            data = await api.get_minute_time_data(TDXParams.MARKET_SH, '600300')
            assert data is not None

            data = await api.get_history_minute_time_data(
                TDXParams.MARKET_SH, '600300', 20161209)
            assert data is not None
            assert type(data) is list
            assert len(data) > 0

            data = await api.get_transaction_data(TDXParams.MARKET_SZ, '000001', 0, 30)
            assert data is not None
            assert type(data) is list

            data = await api.get_history_transaction_data(
                TDXParams.MARKET_SZ, '000001', 0, 10, 20170209)
            assert data is not None
            assert type(data) is list
            assert len(data) == 10

            data = await api.get_company_info_category(TDXParams.MARKET_SZ, '000001')
            assert data is not None
            assert type(data) is list
            assert len(data) > 0

            start = data[0]['start']
            length = data[0]['length']
            data = await api.get_company_info_content(
                0, '000001', '000001.txt', start, length)
            assert data is not None
            assert len(data) > 0

            data = await api.get_xdxr_info(1, '600300')
            assert data is not None
            assert type(data) is list
            assert len(data) > 0

            data = await api.get_finance_info(0, '000001')
            assert data is not None
            assert type(data) is OrderedDict
            assert len(data) > 0

            data = await api.get_k_data('000001', '2017-07-01', '2017-07-10')
            assert type(data) is pd.DataFrame
            assert len(data) == 6

            data = await api.get_and_parse_block_info(TDXParams.BLOCK_FG)
            assert data is not None
            assert type(data) is list
            assert len(data) > 0
        finally:
            await api.close()

    asyncio.run(run())


def test_do_heartbeat():
    async def run():
        api = ATdxHq_API(ip=test_server_ip, raise_exception=True)
        try:
            result = await api.do_heartbeat()
            assert result is not None
            assert result > 0
        finally:
            await api.close()

    asyncio.run(run())


def test_concurrent_requests():
    async def run():
        api = ATdxHq_API(ip=test_server_ip, raise_exception=True, max_connections=6)
        try:
            await api.get_security_count(0)
            tasks = [
                api.get_security_bars(9, 0, '000001', (9 - i) * 800, 800)
                for i in range(3)
            ]
            results = await api.run_until_complete(tasks)
            assert len(results) == 3
            for r in results:
                assert r is not None
                assert type(r) is list
        finally:
            await api.close()

    asyncio.run(run())


def test_to_df():
    api = ATdxHq_API()
    assert isinstance(api.to_df([{'a': 1}, {'a': 2}]), pd.DataFrame)
    assert isinstance(api.to_df({'a': 1}), pd.DataFrame)
    assert isinstance(api.to_df(42), pd.DataFrame)


def test_raise_exception():
    async def run():
        api = ATdxHq_API(ip='114.114.114.114', raise_exception=True)
        try:
            with pytest.raises(Exception):
                await api.get_security_count(0)
        finally:
            await api.close()

    asyncio.run(run())
