# coding: utf-8

import datetime
import asyncio
import struct
from typing import Optional


async def receive_all(send_pkg: bytes, connection: 'AsyncTrafficStatSocket') -> bytes:
    await connection.send(send_pkg)
    head_buf = await connection.recv(0x10)
    if len(head_buf) != 0x10:
        raise ValueError("Failed to receive complete header")
    _, _, _, zipsize, _ = struct.unpack("<IIIHH", head_buf)
    body_buf = bytearray()
    remaining = zipsize
    while remaining > 0:
        buf = await connection.recv(remaining)
        if not buf:
            break
        body_buf.extend(buf)
        remaining -= len(buf)
    return bytes(body_buf)


class AsyncTrafficStatSocket:
    """
    实现支持流量统计的socket类
    """

    def __init__(self, ip: str, port: int, pool: Optional[object] = None):
        self.send_pkg_num: int = 0  # 发送次数
        self.recv_pkg_num: int = 0  # 接收次数
        self.send_pkg_bytes: int = 0  # 发送字节
        self.recv_pkg_bytes: int = 0  # 接收字节数
        self.first_pkg_send_time: Optional[datetime.datetime] = None  # 第一个数据包发送时间

        self.last_api_send_bytes: int = 0  # 最近的一次api调用的发送字节数
        self.last_api_recv_bytes: int = 0  # 最近一次api调用的接收字节数
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.ip: str = ip
        self.port: int = port
        self.pool: Optional[object] = pool
        self.connected: bool = False

    async def connect(self) -> 'AsyncTrafficStatSocket':
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        self.connected = True
        return self

    async def disconnect(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False

    async def send(self, data: bytes, flags: Optional[int] = None) -> int:
        if not (self.reader and self.writer):
            await self.connect()
        nsended = len(data)
        self.writer.write(data)
        await self.writer.drain()
        if self.first_pkg_send_time is None:
            self.first_pkg_send_time = datetime.datetime.now()
        self.send_pkg_num += 1
        self.send_pkg_bytes += nsended
        return nsended

    async def recv(self, buffersize: int, flags: Optional[int] = None) -> bytes:
        if not (self.reader and self.writer):
            await self.connect()
        head_buf = await self.reader.read(buffersize)
        self.recv_pkg_num += 1
        self.recv_pkg_bytes += len(head_buf)  # Use actual received bytes
        return head_buf

    def set_last_api_sent(self, num: int) -> None:
        self.last_api_send_bytes = num  # Fixed typo (was setting recv_bytes)

    def set_last_api_received(self, num: int) -> None:
        self.last_api_recv_bytes = num