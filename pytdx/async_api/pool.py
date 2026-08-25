# coding: utf-8

import asyncio
from typing import Set
from .async_base_socket_client import AsyncTrafficStatSocket


class ConnectionPool:
    def __init__(self, ip: str, port: int, max_connections: int = 100):
        self.max_connections = max_connections
        self.ip = ip
        self.port = port
        self._available: asyncio.Queue[AsyncTrafficStatSocket] = asyncio.Queue()
        self._in_use: Set[AsyncTrafficStatSocket] = set()
        self.created_connect: int = 0

    async def get_connection(self) -> AsyncTrafficStatSocket:
        while True:
            try:
                conn = self._available.get_nowait()
            except asyncio.QueueEmpty:
                if self.created_connect < self.max_connections:
                    conn = self.make_connection()
                    self._in_use.add(conn)
                    return conn
                conn = await self._available.get()

            if conn.connected:
                self._in_use.add(conn)
                return conn
            else:
                await conn.disconnect()
                self.created_connect -= 1

    def make_connection(self) -> AsyncTrafficStatSocket:
        self.created_connect += 1
        return AsyncTrafficStatSocket(self.ip, self.port, pool=self)

    def release(self, connection: AsyncTrafficStatSocket) -> None:
        if connection in self._in_use:
            self._in_use.discard(connection)
            if connection.connected:
                self._available.put_nowait(connection)
            else:
                self.created_connect -= 1

    async def discard(self, connection: AsyncTrafficStatSocket) -> None:
        if connection in self._in_use:
            self._in_use.discard(connection)
            try:
                await connection.disconnect()
            except Exception:
                pass
            self.created_connect -= 1

    async def disconnect(self) -> None:
        all_conns = list(self._in_use)
        while not self._available.empty():
            all_conns.append(self._available.get_nowait())
        for connection in all_conns:
            await connection.disconnect()
        self._in_use.clear()
        self.created_connect = 0

    async def close(self) -> None:
        await self.disconnect()
