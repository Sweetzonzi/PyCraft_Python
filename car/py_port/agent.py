"""
Agent 代理对象。
通过 TCP 向 Java 端发送 agent_command 消息，实现对 CarEntity 的远程控制。
"""
from typing import Optional, Tuple


class AgentProxy:
    """CarEntity 的 Python 代理，所有方法调用通过 TCP 转发到 Java 端。"""

    def __init__(self, client, agent_id: int):
        self._client = client
        self._agent_id = agent_id

    def _sync_request(self, command: str, args: dict = None) -> dict:
        """同步发送 agent_command 请求"""
        if args is None:
            args = {}
        args["agent_id"] = self._agent_id
        args["command"] = command
        return self._client.sync_request("agent_command", args)

    # ====== 驾驶控制 ======

    def drive(self, throttle: float, steering: float, brake: bool = False):
        """设置油门、转向、刹车"""
        self._sync_request("drive", {
            "throttle": throttle,
            "steering": steering,
            "brake": brake
        })

    def handbrake(self):
        """手刹"""
        self._sync_request("handbrake")

    def release_handbrake(self):
        """松开手刹"""
        self._sync_request("release_handbrake")

    # ====== 状态查询 ======

    def get_speed(self) -> float:
        """获取当前速度"""
        resp = self._sync_request("get_speed")
        if resp.get("success"):
            return resp["data"]["speed"]
        return 0.0

    def get_position(self) -> Tuple[float, float, float]:
        """获取位置 (x, y, z)"""
        resp = self._sync_request("get_position")
        if resp.get("success"):
            d = resp["data"]
            return (d["x"], d["y"], d["z"])
        return (0.0, 0.0, 0.0)

    def set_position(self, x: float, y: float, z: float):
        """设置位置"""
        self._sync_request("set_position", {"x": x, "y": y, "z": z})

    def get_rotation(self) -> Tuple[float, float, float, float]:
        """获取旋转四元数 (x, y, z, w)"""
        resp = self._sync_request("get_rotation")
        if resp.get("success"):
            d = resp["data"]
            return (d["x"], d["y"], d["z"], d["w"])
        return (0.0, 0.0, 0.0, 1.0)

    # ====== LineFollowComponent 控制 ======

    def line_follower_set_enabled(self, enabled: bool):
        """启用/禁用巡线"""
        self._sync_request("line_follower_set_enabled", {"enabled": enabled})

    def line_follower_set_throttle(self, throttle: float):
        """设置巡线基础油门"""
        self._sync_request("line_follower_set_throttle", {"throttle": throttle})

    def line_follower_get_error(self) -> float:
        """获取巡线误差"""
        resp = self._sync_request("line_follower_get_error")
        if resp.get("success"):
            return resp["data"]["error"]
        return 0.0

    def line_follower_reset_pid(self):
        """重置巡线 PID"""
        self._sync_request("line_follower_reset_pid")

    def line_follower_set_pid(self, p: float, i: float, d: float):
        """设置巡线 PID 参数"""
        self._sync_request("line_follower_set_pid", {"p": p, "i": i, "d": d})

    # ====== 生命周期控制 ======

    def remove(self):
        """从世界中删除此 agent"""
        self._sync_request("remove_agent")

    # ====== Turtle 步进控制 ======

    def turtle_front(self, blocks: float):
        """向前移动 blocks 格（非阻塞，入队到 Java 端执行）"""
        self._sync_request("turtle_front", {"blocks": blocks})

    def turtle_back(self, blocks: float):
        """向后移动 blocks 格（非阻塞）"""
        self._sync_request("turtle_back", {"blocks": blocks})

    def turtle_turn_left(self, degrees: float):
        """左转 degrees 度（非阻塞）"""
        self._sync_request("turtle_turn_left", {"degrees": degrees})

    def turtle_turn_right(self, degrees: float):
        """右转 degrees 度（非阻塞）"""
        self._sync_request("turtle_turn_right", {"degrees": degrees})

    def turtle_is_busy(self) -> bool:
        """查询是否有命令正在执行或队列非空"""
        resp = self._sync_request("turtle_is_busy")
        if resp.get("success"):
            return resp["data"]["busy"]
        return False

    def turtle_clear(self):
        """清空命令队列并中断当前命令"""
        self._sync_request("turtle_clear")