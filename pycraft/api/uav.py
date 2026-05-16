import asyncio

class UavEntity:
    def __init__(self, level, agent_id):
        self._level = level
        self.agent_id = agent_id

    async def get_state(self):
        resp = await self._level._client.request("get_uav_state", {
            "agent_id": self.agent_id
        })
        if not resp.get("success"):
            raise Exception(f"获取状态失败: {resp.get('error_message')}")
        return resp["data"]

    async def set_target(self, x, y, z):
        resp = await self._level._client.request("set_uav_target", {
            "agent_id": self.agent_id,
            "x": float(x),
            "y": float(y),
            "z": float(z)
        })

        if not resp.get("success"):
            raise Exception(
                resp.get("error_message")
            )
        return True
    
