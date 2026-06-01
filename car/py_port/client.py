"""
TCP 客户端，与 PyCraft 模组的 TCP 服务器通信。
协议：4字节大端长度前缀 + UTF-8 JSON 帧。
"""
import asyncio
import json
import struct
import uuid
from typing import Optional, Dict, Any


class PyModClient:
    """与 Minecraft PyCraft 模组通信的 TCP 客户端（异步）。"""

    def __init__(self, host='localhost', port=8086):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connected = False

    async def connect(self):
        """连接到服务器，成功前每隔1秒重试一次"""
        self._loop = asyncio.get_event_loop()
        while True:
            try:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                asyncio.create_task(self._receive_loop())
                self._connected = True
                break
            except (ConnectionRefusedError, OSError) as e:
                await asyncio.sleep(1)

    async def _receive_loop(self):
        """持续接收响应，匹配 uuid 并设置 Future 结果"""
        while True:
            try:
                length_data = await self.reader.readexactly(4)
                length = struct.unpack('!I', length_data)[0]
                data = await self.reader.readexactly(length)
                response = json.loads(data.decode('utf-8'))
                req_id = response.get('uuid')
                if req_id in self._pending:
                    future = self._pending.pop(req_id)
                    future.set_result(response)
            except (asyncio.IncompleteReadError, ConnectionResetError):
                self._connected = False
                break
            except Exception:
                self._connected = False
                break

    async def request(self, msg_type: str, data: dict) -> dict:
        """发送请求并等待响应"""
        req_id = str(uuid.uuid4())
        msg = {
            "type": msg_type,
            "uuid": req_id,
            "data": data
        }
        json_bytes = json.dumps(msg, separators=(',', ':')).encode('utf-8')
        self.writer.write(struct.pack('!I', len(json_bytes)) + json_bytes)
        await self.writer.drain()

        future = self._loop.create_future()
        self._pending[req_id] = future
        try:
            return await future
        finally:
            self._pending.pop(req_id, None)

    @property
    def connected(self) -> bool:
        return self._connected

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self._connected = False