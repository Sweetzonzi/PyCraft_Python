# pycraft/api/level.py
import asyncio

class Level:
    """
    维度类，保存对维度的引用
    """
    def __init__(self, client, name: str):
        self._client = client
        self.name = name  # 维度标识符，如 "minecraft:overworld"

    async def get_time(self) -> int:
        """
        获取该维度的当前游戏时间（以 tick 为单位）。
        返回时间值（整数），如果请求失败则抛出异常。
        """
        # 发送 get_time 请求，data 中包含维度名称
        resp = await self._client.request("get_time", {"level": self.name})
        if not resp.get("success"):
            error_msg = resp.get("error_message", "Unknown error")
            raise Exception(f"Failed to get time for level {self.name}: {error_msg}")
        # 成功响应中应包含 data.time
        time = resp["data"]["time"]
        return time

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Level('{self.name}')"

    def __eq__(self, other):
        if not isinstance(other, Level):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
    
    async def set_block(self, x: int, y: int, z: int, block: str):
        """
        在指定坐标放置方块block 
        例如: "minecraft:stone"
        """
        resp = await self._client.request("set_block",{"level": self.name,"x": x,"y": y,"z": z,"block": block})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
    async def get_block(self, x: int, y: int, z: int) -> str:
        """
        搜索指定位置方块类型
        """
        resp = await self._client.request("get_block",{"level": self.name,"x": x,"y": y,"z": z})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        block = resp["data"]["block"]
        return block

    async def get_players(self):
        """
        获取该维度中的所有玩家
        """
        resp = await self._client.request("get_players",{"level": self.name})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        from pycraft import Entity
        players = []
        for p in resp["data"]["players"]:
            players.append(Entity(self._client,self,p["id"],p["name"]))
        return players
    
    async def set_blocks(self, x1, y1, z1, x2, y2, z2, block):
        """
        填充一个区域的方块
        """
        resp = await self._client.request("set_blocks",{"level": self.name, "x1": x1,"y1": y1,"z1": z1,"x2": x2,"y2": y2,"z2": z2,"block": block})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
    async def spawn_entity(self, entity_type: str, x: float, y: float, z: float):
        """
        生成实体
        """
        from pycraft.api.entity import Entity
        if ":" not in entity_type:
            entity_type = f"minecraft:{entity_type}"
        payload = {
            "level": self.name,
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "entity_type": entity_type
        }
        resp = await self._client.request("spawn_entity", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        entity_id = resp["data"]["id"]
        return Entity(self._client, self, entity_id, self.name)
    
    async def spawn_particle(self, x, y, z, particle="flame", count=1):
        resp = await self._client.request(
            "spawn_particle",
            {
                "particle": particle,
                "x": x,
                "y": y,
                "z": z,
                "count": count
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
    async def draw_path(self, points, color=0xFF0000, duration=200):
        """
        可视化路径
        :param points: [(x,y,z), ...]
        :param color: 0xRRGGBB
        :param duration: tick（20tick=1秒）
        """
        payload = {
            "points": [list(map(float, p)) for p in points],
            "color": int(color),
            "duration": int(duration)
        }
        resp = await self._client.request("draw_path", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))

# ----- 测试与示例代码 -----
async def main():
    from pycraft import PyModClient
    client = PyModClient()
    try:
        await client.connect()
        levels = await client.get_levels()
        print("Available levels:", [str(lvl) for lvl in levels])
        for level in levels:
            try:
                time = await level.get_time()
                print(f"Time in {level}: {time}")
            except Exception as e:
                print(f"Error getting time for {level}: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())