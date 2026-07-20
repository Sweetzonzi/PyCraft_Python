# pycraft/api/entity.py

from pycraft.api.level import Level
import math
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


    async def move_to(self, x, y, z, speed=0.5):
        """
        须预先规划好轨迹，让实体以一定速度、一定轨迹移动到目标位置
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

    async def navigate_to_entity(self, target: "Entity", speed: float = 1.0) -> dict:
        """
        使用 Minecraft 原生 Mob PathNavigation 向目标实体移动。
        该接口不会自动攻击目标。
        攻击仍应调用：await entity.attack(target)
        speed:
            Minecraft PathNavigation 的速度倍率。该值不是 set_attributes() 中的movement_speed 属性，而是导航速度倍率。
        """
        if target is None:
            raise ValueError("target cannot be None")

        if not hasattr(target, "entity_id"):
            raise TypeError("target must be an Entity with entity_id")

        speed = float(speed)

        if not math.isfinite(speed):
            raise ValueError("speed must be finite")

        if speed <= 0.0:
            raise ValueError("speed must be greater than 0")

        if speed > 10.0:
            raise ValueError("speed cannot be greater than 10")

        resp = await self._client.request(
            "navigate_to_entity",
            {
                "entity_id": self.entity_id,
                "target_id": target.entity_id,
                "speed": speed,
            }
        )

        if not resp.get("success"):
            raise Exception(
                resp.get(
                    "error_message",
                    "navigate_to_entity failed"
                )
            )

        return resp["data"]


    async def stop_navigation(self) -> dict:
        """
        停止实体当前的 Minecraft 原生导航。
        """
        resp = await self._client.request("stop_navigation", {"entity_id": self.entity_id})

        if not resp.get("success"):
            raise Exception(
                resp.get(
                    "error_message",
                    "stop_navigation failed"
                )
            )

        return resp["data"]
    
    async def break_block(self, x: int, y: int, z: int,break_time: float = 5.0) -> dict:
        """
        控制Husk在break_time（单位：s）时间内破坏指定位置的方块。

        注意：
        - 当前 Java 端只允许 Husk 使用此方法。
        - Husk 必须与目标方块处于同一维度。
        - Husk 与方块中心的距离不能超过 4.5 格。
        - 方法返回表示任务已经开始，不表示方块已经破坏完成。
        """
        break_time = float(break_time)

        if not math.isfinite(break_time):
            raise ValueError("break_time must be finite")

        if break_time <= 0:
            raise ValueError("break_time must be greater than 0")

        # Minecraft 通常每秒运行 20 tick
        break_ticks = max(1, round(break_time * 20))

        resp = await self._client.request(
            "break_block",
            {
                "entity_id": self.entity_id,
                "level": self.level.name,
                "x": int(x),
                "y": int(y),
                "z": int(z),
                "break_ticks": break_ticks,
            }
        )

        if not resp.get("success"):
            raise Exception(
                resp.get(
                    "error_message",
                    "break_block failed"
                )
            )

        return resp["data"]

    async def break_blocks(self, blocks, break_time: float = 5.0) -> dict:
        """
        控制Husk在break_time（单位：s）时间内破坏指定位置的多个方块。
        """
        break_time = float(break_time)
        if not math.isfinite(break_time):
            raise ValueError("break_time must be finite")
        if break_time <= 0:
            raise ValueError("break_time must be greater than 0")

        encoded_blocks = []
        seen = set()
        for block in blocks:
            if not isinstance(block, (tuple, list)) or len(block) != 3:
                raise ValueError("each block must be an (x, y, z) tuple or list")
            position = tuple(int(value) for value in block)
            if position not in seen:
                seen.add(position)
                encoded_blocks.append({
                    "x": position[0],
                    "y": position[1],
                    "z": position[2],
                })

        if not encoded_blocks:
            raise ValueError("blocks cannot be empty")
        if len(encoded_blocks) > 256:
            raise ValueError("blocks cannot contain more than 256 positions")

        resp = await self._client.request(
            "break_blocks",
            {
                "entity_id": self.entity_id,
                "level": self.level.name,
                "blocks": encoded_blocks,
                "break_ticks": max(1, round(break_time * 20)),
            }
        )

        if not resp.get("success"):
            raise Exception(resp.get("error_message", "break_blocks failed"))
        return resp["data"]
        
    async def set_overhead_view(self, enabled: bool = True, height: float = 10.0) -> bool:
        """
        开启/关闭俯视强制模式
        enabled: True=开启俯视强制, False=关闭
        height: 相机高度
        """
        resp = await self._client.request("set_overhead", {
            "enabled": enabled,
            "height": height
        })
        return resp.get("success", False)
    
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
    
    async def attack(self, target: 'Entity') -> dict:
        """
        攻击目标实体。
        Returns:
            dict: {
                "hit": bool,           # 是否命中
                "damage_dealt": float, # 造成的伤害值
                "target_health": float,# 目标剩余血量
                ...
            }
        """
        resp = await self._client.request("attack_entity", {
            "attacker_id": self.entity_id,
            "target_id": target.entity_id,
        })
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return resp["data"]
    
    async def set_attributes(self,*,max_health: float | None = None,health: float | None = None,movement_speed: float | None = None,attack_damage: float | None = None,follow_range: float | None = None) -> dict:
        """
        设置生物属性。
        没有传入的属性不会被修改。
        """
        payload = {"entity_id": self.entity_id}
        if max_health is not None:
            payload["max_health"] = float(max_health)
        if health is not None:
            payload["health"] = float(health)
        if movement_speed is not None:
            payload["movement_speed"] = float(movement_speed)
        if attack_damage is not None:
            payload["attack_damage"] = float(attack_damage)
        if follow_range is not None:
            payload["follow_range"] = float(follow_range)
        resp = await self._client.request("set_entity_attributes", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        data = resp["data"]
        if "skipped" in data:
            print(f"Warning: skipped attributes: {data['skipped']}")
        return data
    
    async def get_attributes(self, *attributes: str) -> dict:
        """
        获得生物属性
        """
        payload = {"entity_id": self.entity_id}
        if attributes:
            payload["attributes"] = list(attributes)
        resp = await self._client.request("get_entity_attributes", payload)
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        return resp["data"]

    async def remove(self):
        """
        删除实体
        """
        resp = await self._client.request("remove_entity", {"entity_id": self.entity_id})
        if not resp.get("success"):
            raise Exception(resp.get("error_message"))
        
