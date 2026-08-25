'''parser async'''
from __future__ import annotations
import asyncio
import struct
import zlib
from typing import Type, TypeVar, Any
from pytdx.parser.base import BaseParser
from pytdx.log import DEBUG, log

T = TypeVar('T', bound=BaseParser)


class SendPkgNotReadyError(Exception):
    pass


class ResponseRecvFailsError(Exception):
    pass


def make_async_parser(parser_cls: Type[T], connection: Any) -> T:
    """创建异步版本的解析器"""

    class AsyncParser(parser_cls):
        def __init__(self):
            super().__init__(None, None)
            self._connection = connection

        async def call_api(self) -> Any:
            if self.lock:
                async with self.lock:
                    log.debug("sending thread lock api call")
                    return await self._call_api()
            return await self._call_api()

        async def _call_api(self) -> Any:
            if not self.send_pkg:
                raise SendPkgNotReadyError("send pkg not ready")

            await self._connection.send(self.send_pkg)

            head_buf = await self._recv_exactly(self.rsp_header_len)
            _, _, _, zipsize, unzipsize = struct.unpack("<IIIHH", head_buf)

            body_buf = await self._recv_exactly(zipsize)

            if zipsize != unzipsize:
                log.debug("Decompressing data...")
                loop = asyncio.get_event_loop()
                body_buf = await loop.run_in_executor(None, zlib.decompress, body_buf)

            if DEBUG:
                log.debug("recv body: %s", body_buf[:100])

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
