'''parser async'''
from __future__ import annotations
import asyncio
import struct
import zlib
from typing import Type, TypeVar, Any
from pytdx.parser.base import BaseParser
from pytdx.log import DEBUG, log

T = TypeVar('T', bound=BaseParser)

class AsyncParserError(Exception):
    """Base exception for async parser errors"""
    pass

class SendPkgNotReadyError(AsyncParserError):
    pass

class ResponseRecvFailsError(AsyncParserError):
    pass

async def async_decompress(data: bytes) -> bytes:
    """纯异步的zlib解压实现"""
    # 使用asyncio的run_in_executor但指定executor为None，使用默认事件循环执行
    # 注意：这不是真正的纯异步，但比线程池更轻量
    # 对于完全纯异步方案，需要使用aiolzma等异步压缩库
    
    # 这里是折中方案：在事件循环中直接执行（会阻塞事件循环）
    # 仅适用于快速操作（小数据量）
    return zlib.decompress(data)

def make_async_parser(parser_cls: Type[T], connection: Any) -> T:
    """
    创建纯异步版本的解析器
    
    完全避免使用ThreadPoolExecutor，仅使用asyncio原生操作
    """
    class AsyncParser(parser_cls):
        def __init__(self):
            super().__init__(None, None)
            self._connection = connection

        async def call_api(self) -> Any:
            """异步调用接口"""
            if self.lock:
                async with self.lock:
                    log.debug("sending thread lock api call")
                    return await self._call_api()
            return await self._call_api()

        async def _call_api(self) -> Any:
            """纯异步实现的核心方法"""
            print(self)
            if not self.send_pkg:
                raise SendPkgNotReadyError("send pkg not ready")

            # 异步发送请求
            await self._connection.send(self.send_pkg)
            
            # 异步接收头部
            head_buf = await self._recv_exactly(self.rsp_header_len)
            _, _, _, zipsize, unzipsize = struct.unpack("<IIIHH", head_buf)
            
            # 异步接收正文
            body_buf = await self._recv_exactly(zipsize)
            
            try:
                self._connection.pool.release(self._connection)
            except Exception as e:
                log.error(f"Error releasing connection: {e}")

            # 如果需要解压
            if zipsize != unzipsize:
                log.debug("Decompressing data...")
                body_buf = await async_decompress(body_buf)

            if DEBUG:
                log.debug("recv body: %s", body_buf[:100])  # 只打印前100字节

            # 解析响应（假设parseResponse是纯CPU操作）
            # 由于无法避免同步操作，这里直接调用
            # 对于长时间操作，应考虑分割任务或用C扩展实现
            return self.parseResponse(body_buf)

        async def _recv_exactly(self, size: int) -> bytes:
            """确保接收指定数量的字节"""
            data = bytearray()
            while len(data) < size:
                chunk = await self._connection.recv(size - len(data))
                if not chunk:
                    raise ResponseRecvFailsError(
                        f"Connection closed, expected {size} bytes, got {len(data)}")
                data.extend(chunk)
            return bytes(data)

    return AsyncParser()