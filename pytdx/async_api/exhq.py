# coding=utf-8

#
# Just for practising
#


from functools import wraps
from typing import Optional, List, Any
import asyncio
import pandas as pd
import struct

from pytdx.async_api.pool import ConnectionPool
from pytdx.async_api.reflection_async import make_async_parser
from pytdx.base_socket_client import update_last_ack_time

from pytdx.parser.ex_setup_commands import ExSetupCmd1
from pytdx.parser.ex_get_markets import GetMarkets
from pytdx.parser.ex_get_instrument_count import GetInstrumentCount
from pytdx.parser.ex_get_instrument_quote import GetInstrumentQuote
from pytdx.parser.ex_get_minute_time_data import GetMinuteTimeData
from pytdx.parser.ex_get_history_minute_time_data import GetHistoryMinuteTimeData
from pytdx.parser.ex_get_transaction_data import GetTransactionData
from pytdx.parser.ex_get_history_transaction_data import GetHistoryTransactionData
from pytdx.parser.ex_get_instrument_bars import GetInstrumentBars
from pytdx.parser.ex_get_instrument_info import GetInstrumentInfo
from pytdx.parser.ex_get_history_instrument_bars_range import GetHistoryInstrumentBarsRange
from pytdx.parser.ex_get_instrument_quote_list import GetInstrumentQuoteList


async def receive_all(send_pkg: bytes, connection: 'AsyncTrafficStatSocket') -> bytes:
    await connection.send(send_pkg)
    head_buf = await connection.recv(0x10)
    if len(head_buf) != 0x10:
        raise ValueError("Failed to receive complete header")
    
    _, _, _, zipsize, unzipsize = struct.unpack("<IIIHH", head_buf)
    body_buf = bytearray()
    remaining = zipsize
    while remaining > 0:
        buf = await connection.recv(remaining)
        if not buf:
            break
        body_buf.extend(buf)
        remaining -= len(buf)
    
    return bytes(body_buf)


def exec_command(func):
    @wraps(func)
    async def wrapper(self: 'ATdxExHq_API', *args, **kwargs) -> Any:
        connection = await self.pool.get_connection()
        try:
            if not connection.connected:
                await receive_all(bytearray.fromhex(
                                            "01 01 48 65 00 01 52 00 52 00 54 24 1f 32 c6 e5"
                                            "d5 3d fb 41 1f 32 c6 e5 d5 3d fb 41 1f 32 c6 e5"
                                            "d5 3d fb 41 1f 32 c6 e5 d5 3d fb 41 1f 32 c6 e5"
                                            "d5 3d fb 41 1f 32 c6 e5 d5 3d fb 41 1f 32 c6 e5"
                                            "d5 3d fb 41 1f 32 c6 e5 d5 3d fb 41 cc e1 6d ff"
                                            "d5 ba 3f b8 cb c5 7a 05 4f 77 48 ea"
                ), connection)
            print(connection.connected)
            data = await func(self, *args, **kwargs, connection=connection)
            return data
        finally:
            self.pool.release(connection)

    return wrapper


class ATdxExHq_API:
    def __init__(self, ip: str = '121.14.110.210', port: int = 7727, 
                 auto_retry: bool = False, raise_exception: bool = True):
        self.pool = ConnectionPool(ip=ip, port=port)
        self.auto_retry = auto_retry
        self.raise_exception = raise_exception

    @update_last_ack_time
    @exec_command
    async def get_markets(self, connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetMarkets, connection)
        cmd.setup()
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_instrument_count(self, connection: Optional['AsyncTrafficStatSocket'] = None) -> int:
        cmd = make_async_parser(GetInstrumentCount, connection)
        cmd.setup()
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_instrument_quote(self, market: int, code: str, 
                                   connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetInstrumentQuote, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_instrument_bars(self, category: int, market: int, code: str, start: int = 0, count: int = 700, 
                                  connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetInstrumentBars, connection)
        cmd.setParams(category, market, code, start=start, count=count)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_minute_time_data(self, market: int, code: str, 
                                   connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetMinuteTimeData, connection)
        cmd.setParams(market, code)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_history_minute_time_data(self, market: int, code: str, date: int, 
                                           connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetHistoryMinuteTimeData, connection)
        cmd.setParams(market, code, date=date)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_transaction_data(self, market: int, code: str, start: int = 0, count: int = 1800, 
                                   connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetTransactionData, connection)
        cmd.setParams(market, code, start=start, count=count)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_history_transaction_data(self, market: int, code: str, date: int, start: int = 0, count: int = 1800, 
                                           connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetHistoryTransactionData, connection)
        cmd.setParams(market, code, date, start=start, count=count)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_history_instrument_bars_range(self, market: int, code: str, start: int, end: int, 
                                                connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetHistoryInstrumentBarsRange, connection)
        cmd.setParams(market, code, start, end)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_instrument_info(self, start: int, count: int = 100, 
                                  connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetInstrumentInfo, connection)
        cmd.setParams(start, count)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def get_instrument_quote_list(self, market: int, category: int, start: int = 0, count: int = 80, 
                                        connection: Optional['AsyncTrafficStatSocket'] = None):
        cmd = make_async_parser(GetInstrumentQuoteList, connection)
        cmd.setParams(market, category, start, count)
        return await cmd.call_api()

    @update_last_ack_time
    @exec_command
    async def do_heartbeat(self, connection: Optional['AsyncTrafficStatSocket'] = None) -> int:
        return await self.get_instrument_count(connection=connection)

    async def run_until_complete(self, coroutines: List[Any], **kwargs) -> List[Any]:
        """Run a list of coroutines concurrently and return their results."""
        return await asyncio.gather(*coroutines, **kwargs)

    async def close(self) -> None:
        """Close the API and its connection pool."""
        await self.pool.close()


if __name__ == '__main__':
    import time
    t1 = time.time()

    async def main():
        api = ATdxExHq_API(ip='sztdx.gtjas.com', port=7727)
        try:
            # 测试获取市场代码
            markets = await api.get_markets()
            print("Markets:", markets)

            # 测试获取商品数量
            instrument_count = await api.get_instrument_count()
            print("Instrument Count:", instrument_count)
        finally:
            await api.close()

    asyncio.run(main())
    print("Execution time:", time.time() - t1)
