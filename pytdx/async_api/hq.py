'''tdx异步api接口'''
# coding: utf-8

from typing import Optional, List, Tuple, Union, Any
import asyncio
import random
import time
import pandas as pd

from pytdx.async_api.pool import ConnectionPool
from pytdx.async_api.reflection_async import make_async_parser
from pytdx.async_api.async_base_socket_client import (
    AsyncTrafficStatSocket, make_exec_command, async_update_last_ack_time,
)

from pytdx.parser.get_block_info import GetBlockInfo, GetBlockInfoMeta
from pytdx.parser.get_company_info_category import GetCompanyInfoCategory
from pytdx.parser.get_company_info_content import GetCompanyInfoContent
from pytdx.parser.get_finance_info import GetFinanceInfo
from pytdx.parser.get_history_minute_time_data import GetHistoryMinuteTimeData
from pytdx.parser.get_history_transaction_data import GetHistoryTransactionData
from pytdx.parser.get_index_bars import GetIndexBarsCmd
from pytdx.parser.get_minute_time_data import GetMinuteTimeData
from pytdx.parser.get_security_bars import GetSecurityBarsCmd
from pytdx.parser.get_security_count import GetSecurityCountCmd
from pytdx.parser.get_security_list import GetSecurityList
from pytdx.parser.get_security_quotes import GetSecurityQuotesCmd
from pytdx.parser.get_transaction_data import GetTransactionData
from pytdx.parser.get_xdxr_info import GetXdXrInfo


exec_command = make_exec_command([
    '0c 02 18 93 00 01 03 00 03 00 0d 00 01',
    '0c 02 18 94 00 01 03 00 03 00 0d 00 02',
    '0c 03 18 99 00 01 20 00 20 00 db 0f d5'
    'd0 c9 cc d6 a4 a8 af 00 00 00 8f c2 25'
    '40 13 00 00 d5 00 c9 cc bd f0 d7 ea 00'
    '00 00 02',
])


class ATdxHq_API:
    def __init__(self, ip: str = '101.227.73.20', port: int = 7709, 
                 raise_exception: bool = False, max_connections: int = 6):
        self.pool = ConnectionPool(ip=ip, port=port, max_connections=max_connections)
        self.raise_exception = raise_exception
        self.last_ack_time = time.time()

    def to_df(self, v):
        if isinstance(v, list):
            return pd.DataFrame(data=v)
        elif isinstance(v, dict):
            return pd.DataFrame(data=[v, ])
        else:
            return pd.DataFrame(data=[{'value': v}])

    @async_update_last_ack_time
    @exec_command
    async def get_security_bars(self, category: int, market: int, code: str, 
                              start: int, count: int, connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetSecurityBarsCmd, connection)
        cmd.setParams(category, market, code, start, count)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_index_bars(self, category: int, market: int, code: str, 
                           start: int, count: int, connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetIndexBarsCmd, connection)
        cmd.setParams(category, market, code, start, count)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_security_quotes(self, all_stock: Union[Tuple[int, str], List[Tuple[int, str]]], 
                               code: Optional[str] = None, connection: Optional[AsyncTrafficStatSocket] = None):
        if code is not None:
            all_stock = [(all_stock, code)]
        elif isinstance(all_stock, (list, tuple)) and len(all_stock) == 2 and isinstance(all_stock[0], int):
            all_stock = [all_stock]

        cmd = make_async_parser(GetSecurityQuotesCmd, connection)
        cmd.setParams(all_stock)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_security_count(self, market: int, connection: Optional[AsyncTrafficStatSocket] = None) -> int:
        cmd = make_async_parser(GetSecurityCountCmd, connection)
        cmd.setParams(market)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_security_list(self, market: int, start: int, 
                              connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetSecurityList, connection)
        cmd.setParams(market, start)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_minute_time_data(self, market: int, code: str, 
                                 connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetMinuteTimeData, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_history_minute_time_data(self, market: int, code: str, date: int, 
                                         connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetHistoryMinuteTimeData, connection)
        cmd.setParams(market, code, date)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_transaction_data(self, market: int, code: str, start: int, count: int, 
                                 connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetTransactionData, connection)
        cmd.setParams(market, code, start, count)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_history_transaction_data(self, market: int, code: str, start: int, 
                                         count: int, date: int, connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetHistoryTransactionData, connection)
        cmd.setParams(market, code, start, count, date)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_company_info_category(self, market: int, code: str, 
                                      connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetCompanyInfoCategory, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_company_info_content(self, market: int, code: str, filename: str, 
                                     start: int, length: int, connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetCompanyInfoContent, connection)
        cmd.setParams(market, code, filename, start, length)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_xdxr_info(self, market: int, code: str, 
                          connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetXdXrInfo, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_finance_info(self, market: int, code: str, 
                             connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetFinanceInfo, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_block_info_meta(self, blockfile: str, 
                                connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetBlockInfoMeta, connection)
        cmd.setParams(blockfile)
        return await cmd.call_api()

    @async_update_last_ack_time
    @exec_command
    async def get_block_info(self, blockfile: str, start: int, size: int, 
                           connection: Optional[AsyncTrafficStatSocket] = None):
        cmd = make_async_parser(GetBlockInfo, connection)
        cmd.setParams(blockfile, start, size)
        return await cmd.call_api()

    async def get_and_parse_block_info(self, blockfile: str):
        from pytdx.reader.block_reader import BlockReader, BlockReader_TYPE_FLAT
        meta = await self.get_block_info_meta(blockfile)
        if not meta:
            return None
        size = meta['size']
        one_chunk = 0x7530
        chunks = size // one_chunk + (1 if size % one_chunk != 0 else 0)
        file_content = bytearray()
        for seg in range(chunks):
            start = seg * one_chunk
            piece_data = await self.get_block_info(blockfile, start, size)
            file_content.extend(piece_data)
        return BlockReader().get_data(file_content, BlockReader_TYPE_FLAT)

    @async_update_last_ack_time
    async def do_heartbeat(self) -> int:
        return await self.get_security_count(random.randint(0, 1))

    async def run_until_complete(self, coroutines: List[Any], **kwargs) -> List[Any]:
        """Run a list of coroutines concurrently and return their results."""
        return await asyncio.gather(*coroutines, **kwargs)

    async def close(self) -> None:
        """Close the API and its connection pool."""
        await self.pool.close()

    @async_update_last_ack_time
    async def get_k_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        def __select_market_code(code: str) -> int:
            code = str(code)
            if code[0] in ['5', '6', '9'] or code[:3] in ["009", "126", "110", "201", "202", "203", "204"]:
                return 1  # 上海
            return 0  # 深圳

        market_code = __select_market_code(code)
        tasks = [
            self.get_security_bars(9, market_code, code, (9 - i) * 800, 800)
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        data = pd.concat([self.to_df(result) for result in results], axis=0)

        data = (data
                .assign(date=data['datetime'].astype(str).str[:10], code=str(code))
                .set_index('date', drop=False)
                .drop(columns=['year', 'month', 'day', 'hour', 'minute', 'datetime'])
                .loc[start_date:end_date]
                .assign(date=lambda x: x['date'].astype(str).str[:10]))
        return data


if __name__ == '__main__':
    t1 = time.time()
    async def main():
        api = ATdxHq_API(ip='sztdx.gtjas.com')
        try:
            res = [api.get_history_transaction_data(0, x, 0, 800, 20230911) for x in ['000001', '000002', '000021', '000028', '000050']]
            ress = await api.run_until_complete(res)
            return ress
        finally:
            await api.close()

    results = asyncio.run(main())
    print(time.time() - t1)
