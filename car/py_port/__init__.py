"""
py_port - PyCraft Mod Python 客户端库

通过 TCP 协议与 Minecraft PyCraft 模组通信，控制无人车等 Agent。

快速开始：
    from py_port import get_agent_manager

    mgr = get_agent_manager()
    car = mgr.get_agent(1)
    car.drive(0.6, 0.0, False)
"""
from py_port.agent_manager import AgentManager
from py_port.agent import AgentProxy

# 全局单例
_agent_manager: AgentManager = None


def get_agent_manager() -> AgentManager:
    """
    获取 AgentManager 单例。
    首次调用时自动启动后台连接。
    """
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
        _agent_manager.start()
    return _agent_manager


__all__ = ["get_agent_manager", "AgentManager", "AgentProxy"]