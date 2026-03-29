import asyncio
import json
import struct
import uuid
from typing import Optional, Dict, List

class PyModClient:
    def __init__(self, host='localhost', port=8086):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._pending: Dict[str, asyncio.Future] = {}  # uuid -> Future
        self._loop = asyncio.get_event_loop()

    async def connect(self):
        """持续尝试连接服务器，成功前每隔1秒重试一次"""
        while True:
            try:
                print(f"Connecting to {self.host}:{self.port}...")
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                # 连接成功，启动后台接收任务
                asyncio.create_task(self._receive_loop())
                break  # 退出重试循环
            except (ConnectionRefusedError, OSError) as e:
                # 连接失败，等待1秒后重试
                print(f"Connection failed: {e}. Retrying in 1 second...")
                await asyncio.sleep(1)

    async def _receive_loop(self):
        """持续接收响应，匹配 uuid 并设置 Future 结果"""
        while True:
            try:
                # 读取长度前缀（4字节大端）
                length_data = await self.reader.readexactly(4)
                length = struct.unpack('!I', length_data)[0]
                # 读取 JSON 数据
                data = await self.reader.readexactly(length)
                response = json.loads(data.decode('utf-8'))
                # 根据 uuid 分发
                req_id = response.get('uuid')
                if req_id in self._pending:
                    future = self._pending.pop(req_id)
                    future.set_result(response)
                else:
                    # 无匹配请求ID，可能是服务端主动推送，可记录日志
                    print(f"Unmatched response: {response}")
            except (asyncio.IncompleteReadError, ConnectionResetError):
                # 连接关闭
                break
            except Exception as e:
                print(f"Receive error: {e}")
                break

    async def request(self, msg_type: str, data: dict) -> dict:
        """发送请求并等待响应（自动生成 uuid）"""
        req_id = str(uuid.uuid4())
        # 构造消息
        msg = {
            "type": msg_type,
            "uuid": req_id,
            "data": data
        }
        # 序列化并添加长度前缀
        json_str = json.dumps(msg, separators=(',', ':'))  # 紧凑格式
        json_bytes = json_str.encode('utf-8')
        self.writer.write(struct.pack('!I', len(json_bytes)) + json_bytes)
        await self.writer.drain()

        # 创建 Future 并等待响应
        future = self._loop.create_future()
        self._pending[req_id] = future
        try:
            return await future
        finally:
            # 确保即使取消也清理
            self._pending.pop(req_id, None)

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    # ----- 高层 API -----
    async def get_levels(self) -> List['Level']:
        """获取所有可用维度，返回 Level 对象列表"""
        resp = await self.request("list_level", {})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        # 假设服务器返回的 data 中包含 "levels" 数组，每个元素是维度名称字符串
        level_names = resp["data"]["levels"]
        # 注意：Level 类需要 client 引用，为了避免循环导入，将导入放在方法内
        from pycraft import Level
        return [Level(self, name) for name in level_names]
    
    def overworld(self):
        from pycraft import Level
        return Level(self, "minecraft:overworld")

    def nether(self):
        from pycraft import Level
        return Level(self, "minecraft:the_nether")

    def end(self):
        from pycraft import Level
        return Level(self, "minecraft:the_end")

# 使用示例
async def main():
    client = PyModClient()
    await client.connect()
    try:
        # 查询维度列表
        levels = await client.get_levels()
        print("Available levels:", levels)
        # 取第一个维度
        level_name = levels[0].name
        # 获取时间
        level = levels[0]
        time = await level.get_time()
        print("Game time:", time)

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())