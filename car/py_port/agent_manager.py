"""
Agent 管理器。维护 TCP 连接，提供同步 API 获取 AgentProxy。
"""
import asyncio
import threading
from typing import Optional, Dict

from py_port.client import PyModClient
from py_port.agent import AgentProxy


class AgentManager:
    """
    与 Java 端 AgentManager 对应的 Python 管理器。
    内部维护一个异步事件循环和 TCP 连接，对外提供同步 API。
    """

    def __init__(self, host='localhost', port=8086):
        self._host = host
        self._port = port
        self._client = PyModClient(host, port)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = False

    def start(self) -> bool:
        """
        启动后台线程运行事件循环并连接服务器。
        阻塞直到连接成功。
        """
        self._ready = False
        self._loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_and_run())

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # 等待连接成功
        while not self._client.connected:
            import time
            time.sleep(0.1)
        self._ready = True
        return True

    async def _connect_and_run(self):
        """连接服务器并保持事件循环运行"""
        await self._client.connect()
        # 事件循环保持运行以处理后台接收
        while True:
            await asyncio.sleep(3600)

    def sync_request(self, msg_type: str, data: dict) -> dict:
        """
        同步发送请求。
        在事件循环线程中执行异步请求并等待结果。
        """
        if not self._ready or not self._client.connected:
            raise ConnectionError("Not connected to server")
        future = asyncio.run_coroutine_threadsafe(
            self._client.request(msg_type, data),
            self._loop
        )
        return future.result(timeout=10)

    def get_agent(self, agent_id: int) -> Optional[AgentProxy]:
        """获取 Agent 代理对象（不检查 agent 是否存在，由 Java 端验证）"""
        return AgentProxy(self, agent_id)

    def send_command(self, msg_type: str, data: dict) -> dict:
        """
        发送任意类型的 TCP 命令（例如 set_block, get_block 等非 agent 命令）。
        返回响应字典。
        """
        return self.sync_request(msg_type, data)

    def set_block(self, level: str, x: int, y: int, z: int, block: str) -> bool:
        """
        在指定维度放置一个方块。

        Args:
            level: 维度ID，如 "minecraft:overworld"
            x, y, z: 方块坐标
            block: 方块ID，如 "minecraft:white_wool"
        """
        resp = self.send_command("set_block", {
            "level": level,
            "x": x, "y": y, "z": z,
            "block": block
        })
        return resp.get("success", False)

    def set_blocks(self, level: str, x1: int, y1: int, z1: int,
                   x2: int, y2: int, z2: int, block: str) -> bool:
        """
        在指定维度填充一个区域内的方块。

        Args:
            level: 维度ID，如 "minecraft:overworld"
            x1,y1,z1: 区域一角
            x2,y2,z2: 区域另一角
            block: 方块ID，如 "minecraft:white_wool"
        """
        resp = self.send_command("set_blocks", {
            "level": level,
            "x1": x1, "y1": y1, "z1": z1,
            "x2": x2, "y2": y2, "z2": z2,
            "block": block
        })
        return resp.get("success", False)

    def get_player_pos(self, level: str = "minecraft:overworld") -> tuple:
        """
        获取指定维度中第一个玩家的位置 (x, y, z)。
        y 为玩家脚底 Y 坐标。

        Args:
            level: 维度ID，如 "minecraft:overworld"
        Returns:
            (x, y, z) 三元组，无玩家时返回 None
        """
        # 1. 获取玩家列表
        resp = self.send_command("get_players", {"level": level})
        if not resp.get("success"):
            return None
        players = resp.get("data", {}).get("players", [])
        if not players:
            return None
        player_id = players[0]["id"]

        # 2. 获取该玩家位置
        resp = self.send_command("get_entity_pos", {"entity_id": player_id})
        if not resp.get("success"):
            return None
        pos = resp["data"]
        return (pos["x"], pos["y"], pos["z"])

    def get_block(self, level: str, x: int, y: int, z: int) -> str:
        """
        获取指定位置的方块 ID。

        Args:
            level: 维度ID，如 "minecraft:overworld"
            x, y, z: 方块坐标
        Returns:
            方块ID字符串，如 "minecraft:white_wool"，失败返回 None
        """
        resp = self.send_command("get_block", {
            "level": level,
            "x": x, "y": y, "z": z
        })
        if resp.get("success"):
            return resp["data"].get("block")
        return None

    def list_agents(self) -> list:
        """
        查询服务端所有可用的 agent 列表。

        Returns:
            [{"id": 1, "type": "car_entity"}, ...]  空列表表示查询失败或无 agent
        """
        try:
            resp = self.send_command("agent_command", {"command": "list_agents"})
            if resp.get("success"):
                return resp.get("data", {}).get("agents", [])
        except Exception as e:
            print(f"[AgentManager] list_agents 失败: {e}")
        return []

    def stop(self):
        """关闭连接"""
        if self._client.connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.close(),
                self._loop
            )
        self._ready = False