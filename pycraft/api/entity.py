# pycraft/api/entity.py

from pycraft.api.level import Level
import asyncio


class Entity:
    """
    实体实例的引用
    """

    def __init__(self, client, level: Level, entity_id: int, name: str):
        self._client = client
        self.level = level
        self.entity_id = entity_id
        self.name = name

    def __repr__(self):
        return f"<Entity id={self.entity_id} name={self.name}>"

    async def get_pos(self):
        """
        获取实体位置
        """
        resp = await self._client.request("get_entity_pos", {"entity_id": self.entity_id})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        data = resp["data"]
        return (data["x"], data["y"], data["z"])

    async def teleport(self, x, y, z):
        """
        瞬移实体
        """
        resp = await self._client.request("teleport_entity", {"entity_id": self.entity_id, "x": x, "y": y, "z": z})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))


    async def move_to(self, x, y, z, speed=0.2):
        """
        让实体以一定速度移动到目标位置
        """
        resp = await self._client.request(
            "move_entity",
            {
                "entity_id": self.entity_id,
                "x": x,
                "y": y,
                "z": z,
                "speed": speed
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
    
    async def set_perspective(self, mode: int = 0) -> bool:
        """
        切换玩家视角
        param mode: 0 - 第一人称, 1 - 第三人称背面, 2 - 第三人称正面
        return: 是否设置成功
        """
        if mode not in (0, 1, 2):
            raise ValueError(f"Invalid perspective mode: {mode}")
        # 发送请求到 Java 端
        resp = await self._client.request("set_perspective", {"mode": mode})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return True

    async def set_rotation(self, yaw: float, pitch: float = 90.0):
        resp = await self._client.request("set_rotation", {"yaw": yaw, "pitch": pitch})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return True
    
    async def get_rotation(self) -> tuple[float, float]:
        resp = await self._client.request("get_rotation", {})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        data = resp.get("data", {})
        return data["yaw"], data["pitch"]
    
    async def attack(self, target) -> bool:
        """
        攻击实体
        """
        resp = await self._client.request(
            "attack_entity",
            {
                "player_id": self.entity_id,
                "target_id": target.entity_id
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return resp["data"]["hit"]

    async def remove(self): # 似乎有些问题
        """
        删除实体
        """
        resp = await self._client.request("remove_entity", {"entity_id": self.entity_id})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
