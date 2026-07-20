# pycraft/api/level.py
import asyncio
from pycraft.api.uav import UavEntity

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
        
    async def spawn_entity(self, entity_type: str, x: float, y: float, z: float, is_agent: bool = False):
        """
        生成实体 / Agent
        """
        from pycraft.api.entity import Entity

        if ":" not in entity_type:
            entity_type = f"minecraft:{entity_type}"

        payload = {
            "level": self.name,
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "entity_type": entity_type,
            "is_agent": is_agent
        }

        resp = await self._client.request("spawn_entity", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        entity_id = resp["data"]["id"]
        return Entity(self._client, self, entity_id, self.name)
    
    async def get_entities(self, type: str = "all"):
        """
        获取实体列表
        :param type: "all" / "monster"
        :return: list[Entity]
        """
        from pycraft.api.entity import Entity
        payload = {
            "level": self.name,
            "type": type
        }
        resp = await self._client.request("get_entities", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        entities = []
        for e in resp["data"]["entities"]:
            entity = Entity(
                self._client,
                self,
                e["id"],
                self.name
            )
            entity.type = e["type"]
            entity.pos = (e["x"], e["y"], e["z"])
            entity.health = e["health"]
            entities.append(entity)
        return entities

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
        
    async def draw_path(self, points, color=0xFFFFFFFF, duration=200):
        """
        可视化路径

        :param points: [(x,y,z), ...]
        :param color: 颜色，默认白色无透明度
        :param duration: 持续时间(帧)
        """
        payload = {
            "points": [list(map(float, p)) for p in points],
            "color": int(color),
            "duration": int(duration)
        }

        resp = await self._client.request("draw_path", payload)

        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
    async def spawn_uav(self, x, y, z):
        """
        在游戏中生成uav agent
        """
        resp = await self._client.request(
            "spawn_uav",
            {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        agent_id = resp["data"]["agent_id"]
        return UavEntity(self, agent_id)

    async def spawn_algorithm(self, x, y, z):
        """
        在游戏中生成 AlgorithmAgent，并返回 agent_id
        """
        resp = await self._client.request(
            "spawn_algorithm",
            {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            }
        )

        if not resp.get("success"):
            raise Exception(resp.get("error_message"))

        return resp["data"]["agent_id"]

    async def get_uav_list(self):
        """
        获取无人机列表
        """
        resp = await self._client.request("get_uav_list", {})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return resp["data"]["uavs"]
    
    async def remove_uav(self, agent_id):
        """
        删除指定ID的无人机
        """
        resp = await self._client.request(
            "remove_uav",
            {
                "agent_id": int(agent_id)
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return True
    
    async def clear_uav(self):
        """
        清除环境内所有的无人机
        """
        resp = await self._client.request(
            "clear_uav",
            {}
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return True

    async def set_container_item(self, x, y, z, slot, item, count=1):
        """
        向指定容器槽位放入物品。
        """
        if not isinstance(item, str):
            raise TypeError("item must be a string")

        if ":" not in item:
            item = f"minecraft:{item}"

        slot = int(slot)
        count = int(count)

        if slot < 0:
            raise ValueError("slot cannot be negative")
        if count <= 0:
            raise ValueError("count must be greater than 0")
        resp = await self._client.request(
            "set_container_item",
            {
                "level": self.name,
                "x": int(x),
                "y": int(y),
                "z": int(z),
                "slot": slot,
                "item": item,
                "count": count
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message","Failed to set container item"))
        return resp["data"]

    async def get_container_items(self, x, y, z):
        """
        获取指定容器中所有非空槽位的物品。
        """
        resp = await self._client.request(
            "get_container_items",
            {
                "level": self.name,
                "x": int(x),
                "y": int(y),
                "z": int(z)
            }
        )
        if not resp.get("success"):
            raise Exception(resp.get("error_message","Failed to get container items"))
        return resp["data"]["items"]

    async def get_container_info(self, x, y, z):
        """
        获取容器的完整信息。
        """
        resp = await self._client.request(
            "get_container_items",
            {
                "level": self.name,
                "x": int(x),
                "y": int(y),
                "z": int(z)
            }
        )

        if not resp.get("success"):
            raise Exception(resp.get("error_message","Failed to get container items"))
        return resp["data"]

    async def take_container_item(self,player_id,x,y,z,slot,count=1):
        """
        从容器指定槽位取出物品，并放入玩家背包。
        """
        resp = await self._client.request(
            "take_container_item",
            {
                "level": self.name,
                "player_id": int(player_id),
                "x": int(x),
                "y": int(y),
                "z": int(z),
                "slot": int(slot),
                "count": int(count)
            }
        )

        if not resp.get("success"):
            raise Exception(resp.get("error_message","Failed to take container item"))

        return resp["data"]

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