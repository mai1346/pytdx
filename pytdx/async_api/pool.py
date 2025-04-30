# coding: utf-8

import os
import asyncio
from itertools import chain
from typing import Set, List
from .async_base_socket_client import AsyncTrafficStatSocket

class ConnectionPool:
    def __init__(self, ip: str, port: int, max_connections: int = 100):
        self.pid = os.getpid()
        self.max_connections = max_connections
        self.ip = ip
        self.port = port
        self._available_connections: List[AsyncTrafficStatSocket] = []
        self.created_connect: int = 0
        self._in_use_connections: Set[AsyncTrafficStatSocket] = set()

    async def get_connection(self) -> AsyncTrafficStatSocket:
        try:
            if self.created_connect >= self.max_connections:
                while not self._available_connections:
                    await asyncio.sleep(0.2)
            connection = self._available_connections.pop()
        except IndexError:
            connection = self.make_connection()

        self._in_use_connections.add(connection)
        return connection

    def make_connection(self) -> AsyncTrafficStatSocket:
        self.created_connect += 1
        return AsyncTrafficStatSocket(self.ip, self.port, pool=self)

    def release(self, connection: AsyncTrafficStatSocket) -> None:
        if connection in self._in_use_connections:
            self._in_use_connections.remove(connection)
            self._available_connections.append(connection)

    async def disconnect(self) -> None:
        """Disconnects all connections in the pool."""
        all_conns = list(chain(self._available_connections, self._in_use_connections))
        for connection in all_conns:
            await connection.disconnect()
        self._available_connections.clear()
        self._in_use_connections.clear()

    async def close(self) -> None:
        """Close the pool and disconnect all connections."""
        await self.disconnect()