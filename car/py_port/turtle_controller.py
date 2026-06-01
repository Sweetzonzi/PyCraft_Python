import time
from py_port import get_agent_manager


class TurtleController:
    """
    海龟控制器。内部使用 AgentProxy 的 turtle_* 命令，
    所有 front/back/left/right 方法均为阻塞式，等待动作完成才返回。
    """

    def __init__(self, agent_id, poll_interval=0.05):
        """
        Args:
            agent_id: 小车的 agent ID（int）
            poll_interval: 轮询完成状态的间隔（秒），默认 0.05
        """
        self._agent = get_agent_manager().get_agent(agent_id)
        self._poll_interval = poll_interval

    # ========== 高层 API ==========

    def front(self, blocks: float):
        """向前移动指定格数（阻塞直到完成）"""
        self._agent.turtle_front(blocks)
        self._wait_for_completion()

    def back(self, blocks: float):
        """向后移动指定格数（阻塞直到完成）"""
        self._agent.turtle_back(blocks)
        self._wait_for_completion()

    def left(self, degrees: float):
        """向左旋转指定角度（阻塞直到完成）"""
        self._agent.turtle_turn_left(degrees)
        self._wait_for_completion()

    def right(self, degrees: float):
        """向右旋转指定角度（阻塞直到完成）"""
        self._agent.turtle_turn_right(degrees)
        self._wait_for_completion()

    # ========== 辅助方法 ==========

    def clear(self):
        """清空队列并急停"""
        self._agent.turtle_clear()

    def is_busy(self) -> bool:
        """查询是否正在执行命令"""
        return self._agent.turtle_is_busy()

    def wait_for_completion(self):
        """阻塞直到所有命令执行完毕"""
        self._wait_for_completion()

    def _wait_for_completion(self):
        """内部轮询等待"""
        while self._agent.turtle_is_busy():
            time.sleep(self._poll_interval)


if __name__ == "__main__":
    import sys

    car_id = 1
    if len(sys.argv) > 1:
        car_id = int(sys.argv[1])

    print(f"[TurtleController] Controlling car {car_id}")

    t = TurtleController(car_id)

    # 示例：走一个矩形
    print("front 5...")
    t.front(5)

    print("left 90...")
    t.left(90)

    print("front 5...")
    t.front(5)

    print("left 90...")
    t.left(90)

    print("front 5...")
    t.front(5)

    print("left 90...")
    t.left(90)

    print("front 5...")
    t.front(5)

    print("left 90...")
    t.left(90)

    print("矩形完成！")