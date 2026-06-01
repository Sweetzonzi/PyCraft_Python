
import sys
import os


def _find_project_root():
    """从脚本位置向上查找项目根目录（包含 py_port/ Python 包的目录）"""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        py_port_dir = os.path.join(current, "py_port")
        if os.path.isdir(py_port_dir) and os.path.isfile(os.path.join(py_port_dir, "__init__.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


_project_root = _find_project_root()
if _project_root and _project_root not in sys.path:
    sys.path.insert(0, _project_root)
del _project_root, _find_project_root

from py_port import get_agent_manager
import time


# 赛道生成
class TrackBuilder:
    """
    在超平坦世界中生成正方形测试赛道。
    白色羊毛为背景，黑色羊毛组成 1 格宽正方形线路，外围 3 格白色边框。
    底部黑线中间放置 3x3 绿色羊毛起点，顶部黑线中间放置 3x3 红色羊毛终点。
    """

    # 赛道区域范围（15x15）
    AREA_SIZE = 15
    # 黑线距外边缘的距离（同时也是外围白线宽度）
    OFFSET = 3

    def __init__(self, mgr, level="minecraft:overworld", y=0):
        """
        Args:
            mgr: AgentManager 实例
            level: 维度ID
            y: 地面Y坐标（超平坦草方块顶层Y）
        """
        self.mgr = mgr
        self.level = level
        self.y = y
        self.origin_x = 0   # 赛道起始X
        self.origin_z = 0   # 赛道起始Z

    def set_origin(self, x, z):
        """设置赛道起点位置"""
        self.origin_x = x
        self.origin_z = z

    def _fill_area(self, x1, z1, x2, z2, block):
        """填充矩形区域"""
        ok = self.mgr.set_blocks(
            self.level,
            self.origin_x + x1, self.y, self.origin_z + z1,
            self.origin_x + x2, self.y, self.origin_z + z2,
            block
        )
        if not ok:
            print(f"[Track] 放置方块失败: {block} 于 ({x1},{z1})-({x2},{z2})")
        return ok

    def _set_block(self, x, z, block):
        """放置单个方块"""
        ok = self.mgr.set_block(
            self.level,
            self.origin_x + x, self.y, self.origin_z + z,
            block
        )
        return ok

    def build(self):
        """
        生成正方形赛道（15x15 区域）：
        - 全部铺白色羊毛（背景 + 外围 3 格白线 + 内部白区）
        - 在偏移 3 格的位置铺 1 格宽黑色正方形环
        - 底部黑线中间放置 3x3 绿色起点
        - 顶部黑线中间放置 3x3 红色终点
        """
        size = self.AREA_SIZE
        off = self.OFFSET  # 3

        print(f"[Track] 正在生成正方形赛道: 原点({self.origin_x},{self.origin_z}), Y={self.y}")
        print(f"[Track] 区域 {size}x{size}, 1格宽黑线, 外围{off}格白色边框")

        # 1. 全部填充为白色羊毛
        print("[Track] 铺设白色背景...")
        self._fill_area(0, 0, size - 1, size - 1, "minecraft:white_wool")
        time.sleep(0.5)

        # 2. 铺设 1 格宽黑色正方形环（距外边缘 3 格）
        print("[Track] 铺设黑色线路...")
        black_count = 0
        for x in range(size):
            for z in range(size):
                # 黑线位置：z=off 顶部边、z=size-1-off 底部边、x=off 左边、x=size-1-off 右边
                on_top    = z == off and off <= x <= size - 1 - off
                on_bottom = z == size - 1 - off and off <= x <= size - 1 - off
                on_left   = x == off and off <= z <= size - 1 - off
                on_right  = x == size - 1 - off and off <= z <= size - 1 - off
                if on_top or on_bottom or on_left or on_right:
                    self._set_block(x, z, "minecraft:black_wool")
                    black_count += 1

        print(f"[Track] 赛道生成完成！共放置 {black_count} 个黑色羊毛")

        # 3. 放置绿色起点 3x3（底部黑线中间）和红色终点 3x3（顶部黑线中间）
        start_x = size // 2
        start_z = size - 1 - off  # 底部黑线中间
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                self._set_block(start_x + dx, start_z + dz, "minecraft:green_wool")
        print(f"[Track] 绿色起点 3x3 已放置，中心于 ({start_x}, {start_z})")

        finish_x = size // 2
        finish_z = off  # 顶部黑线中间
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                self._set_block(finish_x + dx, finish_z + dz, "minecraft:red_wool")
        print(f"[Track] 红色终点 3x3 已放置，中心于 ({finish_x}, {finish_z})")

        # 推荐起点：绿色方块上，车头朝北方（-Z）
        print(f"[Track] 起点推荐: 绿色羊毛 ({start_x},{start_z}) 位置，")
        print(f"[Track]           车头朝向 Z 负方向（地图北方）")
        print(f"[Track]           世界坐标为 ({self.origin_x + start_x}, {self.y + 1}, {self.origin_z + start_z})")
        print(f"[Track]           终点红色羊毛位于 ({self.origin_x + finish_x}, {self.y + 1}, {self.origin_z + finish_z})")

        # 验证赛道
        print("[Track] 验证赛道...")
        test_center = self.origin_x + size // 2, self.origin_z + size // 2
        block_center = self.mgr.get_block(self.level, test_center[0], self.y, test_center[1])
        print(f"[Track]   中心 ({test_center[0]},{self.y},{test_center[1]}) = {block_center}（应为白色）")
        test_path = self.origin_x + start_x, self.origin_z + start_z
        block_path = self.mgr.get_block(self.level, test_path[0], self.y, test_path[1])
        print(f"[Track]   起点 ({test_path[0]},{self.y},{test_path[1]}) = {block_path}（应为绿色）")
        test_finish = self.origin_x + finish_x, self.origin_z + finish_z
        block_finish = self.mgr.get_block(self.level, test_finish[0], self.y, test_finish[1])
        print(f"[Track]   终点 ({test_finish[0]},{self.y},{test_finish[1]}) = {block_finish}（应为红色）")


# 方案A：Java 组件控制（推荐）
class LineFollowController:
    """
    方案A - Java 组件控制

    激活小车内置的 LineFollowComponent，所有传感器读取和 PID 计算在 Java 端完成。
    Python 只需激活组件、设置参数、定期监控状态。

    自绿块/红块功能上线后，小车在布防后不会立即移动，而是等待传感器检测到
    绿色羊毛才自动启动巡线；到达红色羊毛时自动停止。
    """

    def __init__(self, car_id):
        self.car_id = car_id
        self.mgr = get_agent_manager()
        self.car = self.mgr.get_agent(car_id)
        self._started = False

    def start(self, throttle=0.6):
        """布防巡线组件并设置参数（小车需检测到绿块才会启动）"""
        self.car.line_follower_set_throttle(throttle)
        self.car.line_follower_set_enabled(True)
        self._started = True
        print(f"[LineFollow] Armed car {self.car_id} with throttle={throttle}, waiting for green block...")

    def stop(self):
        """停用巡线组件，恢复手动控制"""
        if self._started:
            self.car.line_follower_set_enabled(False)
            self.car.drive(0, 0, True)  # 刹车
            self._started = False
            print("[LineFollow] Stopped")

    def get_status(self):
        """获取巡线状态用于监控"""
        if not self._started:
            return {"enabled": False, "error": 0.0}
        error = self.car.line_follower_get_error()
        return {
            "enabled": True,
            "error": error,
        }

    def set_throttle(self, throttle):
        """运行时调整油门"""
        self.car.line_follower_set_throttle(throttle)
        print(f"[LineFollow] Throttle set to {throttle}")

    def reset_pid(self):
        """重置 PID 控制器"""
        self.car.line_follower_reset_pid()
        print("[LineFollow] PID reset")

    def set_pid(self, p, i, d):
        """运行时调整 PID 参数"""
        self.car.line_follower_set_pid(p, i, d)
        print(f"[LineFollow] PID set to P={p}, I={i}, D={d}")

    def monitor(self, duration=10, interval=0.5):
        """监控巡线状态一段时间"""
        end = time.time() + duration
        while time.time() < end:
            status = self.get_status()
            print(f"[Monitor] enabled={status['enabled']}, "
                  f"error={status['error']:.3f}")
            time.sleep(interval)


# 入口
def main():
    import argparse

    parser = argparse.ArgumentParser(description="无人车自动寻线")
    parser.add_argument("car_id", nargs="?", type=int, default=1,
                        help="小车ID（默认 1）")
    parser.add_argument("--y", type=int, default=None,
                        help="地面Y坐标（默认自动检测玩家所在位置）")
    parser.add_argument("--build-only", action="store_true",
                        help="仅生成赛道，不启动巡线")
    parser.add_argument("--origin-x", type=int, default=None,
                        help="赛道起始X（默认以玩家位置为中心）")
    parser.add_argument("--origin-z", type=int, default=None,
                        help="赛道起始Z（默认以玩家位置为中心）")
    args = parser.parse_args()

    mgr = get_agent_manager()

    # 自动获取玩家位置
    player_pos = mgr.get_player_pos()
    if player_pos is None:
        print("[Main] 无法获取玩家位置，请确认已在游戏中")
        return

    px, py, pz = player_pos
    # 玩家脚底所在方块 Y = floor(feet_y) - 1
    # 例如：站在 Y=0 的草方块上，脚底 Y≈1.0，方块 Y = floor(1.0)-1 = 0
    track_y = args.y if args.y is not None else int(py) - 1
    ox = args.origin_x if args.origin_x is not None else int(px) - 5
    oz = args.origin_z if args.origin_z is not None else int(pz) - 5

    print(f"[Main] 玩家位置: ({px:.1f}, {py:.1f}, {pz:.1f})")
    print(f"[Main] 赛道原点: ({ox}, {track_y}, {oz})")

    # 生成赛道
    builder = TrackBuilder(mgr, level="minecraft:overworld", y=track_y)
    builder.set_origin(ox, oz)
    builder.build()

    if args.build_only:
        print("[Main] 赛道已生成，--build-only 指定，不启动巡线")
        return

    # 等待用户放置小车
    print()
    print("=" * 50)
    print("  请用刷怪蛋生成小车，放在线路起点位置")
    print("  建议放在正方形底部中间的绿色羊毛上，车头朝地图北方（-Z方向）")
    print("  准备好后按 Enter 开始巡线...")
    print("=" * 50)
    input()

    # 诊断：检查小车所在位置的方块
    print()
    print("[Main] 检查小车位置...")
    car = mgr.get_agent(args.car_id)
    cx, cy, cz = car.get_position()
    print(f"[Main]   小车位置: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
    # 检查小车正下方的方块（地面 Y 在 car_y-1 附近）
    ground_y = int(cy) - 1  # 小车中心下方约 0.6 格
    block_below = mgr.get_block("minecraft:overworld", int(cx), ground_y, int(cz))
    print(f"[Main]   小车下方 ({int(cx)},{ground_y},{int(cz)}) = {block_below}")
    # 也检查地面 Y = track_y 的方块
    block_track = mgr.get_block("minecraft:overworld", int(cx), track_y, int(cz))
    print(f"[Main]   赛道层 ({int(cx)},{track_y},{int(cz)}) = {block_track}")

    # 启动巡线
    print()
    ctrl = LineFollowController(args.car_id)
    ctrl.start(throttle=0.6)

    try:
        ctrl.monitor(duration=30000, interval=0.5)
    except KeyboardInterrupt:
        print("\n[Main] 用户中断")
    finally:
        ctrl.stop()

    print("[Main] Done")


if __name__ == "__main__":
    main()