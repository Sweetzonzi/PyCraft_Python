import asyncio

class UavEntity:
    def __init__(self, client, agent_id):
        self._client = client
        self.agent_id = agent_id

    async def get_state(self):
        resp = await self._client.request("get_uav_state", {
            "agent_id": self.agent_id
        })

        if not resp.get("success"):
            raise Exception(f"获取状态失败: {resp.get('error_message')}")

        return resp["data"]

    async def set_target(self, x, y, z):
        resp = await self._client.request("set_uav_target", {
            "agent_id": self.agent_id,
            "x": float(x),
            "y": float(y),
            "z": float(z)
        })

        return resp.get("success", False)
    
    async def get_uav_list(client):
        resp = await client.request("get_uav_list", {})

        if not resp.get("success"):
            raise Exception(resp.get("error_message"))

        return resp["data"]["uavs"]
    
