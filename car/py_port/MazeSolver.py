import random
import heapq
import math
import time
import sys
import os


def _find_project_root():
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

GRID_SIZE = 5             # 5×5 逻辑网格
CELL_SIZE = 3             # 每个 cell 3×3 格开放空间（3 格宽通道）
WALL_SIZE = 1             # 墙厚 1 格
BLOCK_SIZE = GRID_SIZE * (CELL_SIZE + WALL_SIZE) + WALL_SIZE  # 41 格每边
STEP = CELL_SIZE + WALL_SIZE  # 4 — 每个 cell 的步长（墙+通道）
HALF_CELL = CELL_SIZE // 2    # 1 — 用于计算中间块偏移

# 方向：(dr, dc) — N, S, W, E
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# 迷宫生成 — 递归回溯法
class MazeGenerator:
    def __init__(self, size=GRID_SIZE, seed=42):
        self.size = size
        self.seed = seed
        self.walls = None
        self._generate()
    def _generate(self):
        rng = random.Random(self.seed)
        size = self.size
        self.walls = [[[True, True, True, True] for _ in range(size)] for _ in range(size)]
        visited = [[False] * size for _ in range(size)]
        def in_bounds(r, c):
            return 0 <= r < size and 0 <= c < size
        def carve(r, c):
            visited[r][c] = True
            order = list(range(4))
            rng.shuffle(order)
            for d in order:
                dr, dc = DIRS[d]
                nr, nc = r + dr, c + dc
                if in_bounds(nr, nc) and not visited[nr][nc]:
                    self.walls[r][c][d] = False
                    self.walls[nr][nc][d ^ 1] = False  # 对面方向
                    carve(nr, nc)
        carve(0, 0)
    def has_wall(self, r, c, d):
        return self.walls[r][c][d]


# A* 寻路
class AStarPathfinder:
    def __init__(self, maze):
        self.maze = maze
    def find_path(self, start=(GRID_SIZE - 1, GRID_SIZE - 1), end=(0, 0)):
        size = self.maze.size
        walls = self.maze.walls
        def heuristic(r, c):
            return abs(r - end[0]) + abs(c - end[1])
        open_set = [(heuristic(start[0], start[1]), 0, start)]
        came_from = {}
        g_score = {start: 0}
        while open_set:
            _, cost, current = heapq.heappop(open_set)
            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path
            r, c = current
            for d, (dr, dc) in enumerate(DIRS):
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size and not walls[r][c][d]:
                    neighbor = (nr, nc)
                    tentative = g_score[current] + 1
                    if neighbor not in g_score or tentative < g_score[neighbor]:
                        g_score[neighbor] = tentative
                        f = tentative + heuristic(nr, nc)
                        heapq.heappush(open_set, (f, tentative, neighbor))
                        came_from[neighbor] = current
        return None  # 无路径

# Minecraft 迷宫建造
class MazeBuilder:
    def __init__(self, mgr, level, px, py, pz):
        self.mgr = mgr
        self.level = level
        self.px = int(px)                # 玩家 X（迷宫东南角）
        self.py = int(py)                # 玩家 Y（迷宫底层）
        self.pz = int(pz)                # 玩家 Z（迷宫东南角）
        self.origin_x = self.px - (BLOCK_SIZE - 1)
        self.origin_z = self.pz - (BLOCK_SIZE - 1)
    def _set_blocks(self, x1, z1, x2, z2, block):
        self.mgr.set_blocks(
            self.level,
            x1, self.py, z1,
            x2, self.py + 2, z2,
            block
        )
    def _fill_floor(self, x1, z1, x2, z2, block):
        self.mgr.set_blocks(
            self.level,
            x1, self.py - 1, z1,
            x2, self.py - 1, z2,
            block
        )
    def build(self, maze):
        size = maze.size
        print(f"[MazeBuilder] Building maze at origin ({self.origin_x}, {self.py}, {self.origin_z})")
        print(f"[MazeBuilder] Maze size: {BLOCK_SIZE}x{BLOCK_SIZE}x3 blocks")
        print(f"[MazeBuilder] Corridor width: {CELL_SIZE} blocks")
        # 1. 放置所有水平墙（行方向）
        print("[MazeBuilder] Placing horizontal walls...")
        for r in range(size + 1):
            br = r * STEP
            z = self.origin_z + br
            # 水平墙: 从西到东 (origin_x ~ px), 1 格厚, 3 层高
            self._set_blocks(self.origin_x, z, self.px, z, "minecraft:stone")

        # 2. 放置所有垂直墙（列方向）
        print("[MazeBuilder] Placing vertical walls...")
        for c in range(size + 1):
            bc = c * STEP
            x = self.origin_x + bc
            # 垂直墙: 从北到南 (origin_z ~ pz), 1 格厚, 3 层高
            self._set_blocks(x, self.origin_z, x, self.pz, "minecraft:stone")

        # 3. 打通通道（移除迷宫内部墙的特定部分）
        print("[MazeBuilder] Carving passages...")
        passage_count = 0
        for r in range(size):
            for c in range(size):
                # 南向通道 (cell (r,c) -> (r+1,c)) — 3 格宽开口
                if r < size - 1 and not maze.walls[r][c][1]:
                    br = (r + 1) * STEP
                    z = self.origin_z + br
                    x1 = self.origin_x + c * STEP + 1
                    x2 = self.origin_x + c * STEP + CELL_SIZE
                    self._set_blocks(x1, z, x2, z, "minecraft:air")
                    passage_count += 1

                # 东向通道 (cell (r,c) -> (r,c+1)) — 3 格宽开口
                if c < size - 1 and not maze.walls[r][c][3]:
                    bc = (c + 1) * STEP
                    x = self.origin_x + bc
                    z1 = self.origin_z + r * STEP + 1
                    z2 = self.origin_z + r * STEP + CELL_SIZE
                    self._set_blocks(x, z1, x, z2, "minecraft:air")
                    passage_count += 1

        # 4. 打通入口（东南角外墙）
        entrance_r = size - 1
        entrance_c = size - 1
        # 南外墙 (Z = pz)
        for dc in range(CELL_SIZE):
            x = self.origin_x + entrance_c * STEP + 1 + dc
            self._set_blocks(x, self.pz, x, self.pz, "minecraft:air")
        # 东外墙 (X = px)
        for dr in range(CELL_SIZE):
            z = self.origin_z + entrance_r * STEP + 1 + dr
            self._set_blocks(self.px, z, self.px, z, "minecraft:air")

        # 5. 打通出口（西北角外墙）
        exit_r = 0
        exit_c = 0
        # 北外墙 (Z = origin_z)
        for dc in range(CELL_SIZE):
            x = self.origin_x + exit_c * STEP + 1 + dc
            self._set_blocks(x, self.origin_z, x, self.origin_z, "minecraft:air")
        # 西外墙 (X = origin_x)
        for dr in range(CELL_SIZE):
            z = self.origin_z + exit_r * STEP + 1 + dr
            self._set_blocks(self.origin_x, z, self.origin_x, z, "minecraft:air")

        print(f"[MazeBuilder] Carved {passage_count} passages + entrance/exit")

        # 6. 填充整个迷宫地面为白色羊毛（墙底下一整层）
        print("[MazeBuilder] Filling entire maze floor with white wool...")
        self._fill_floor(self.origin_x, self.origin_z, self.px, self.pz, "minecraft:white_wool")

        # 7. 入口 cell (9,9) 中心 3x3 绿色羊毛（供玩家识别入口位置，触发巡线启动）
        entrance_r = size - 1
        entrance_c = size - 1
        ex0 = self.origin_x + entrance_c * STEP + 1
        ez0 = self.origin_z + entrance_r * STEP + 1
        self._fill_floor(ex0, ez0, ex0 + 2, ez0 + 2, "minecraft:green_wool")
        print(f"[MazeBuilder] Green wool 3x3 at entrance cell ({entrance_r},{entrance_c})")

        print("[MazeBuilder] Maze building complete!")

    def mark_path(self, path):
        if not path:
            print("[MazeBuilder] No path to mark!")
            return

        print(f"[MazeBuilder] Marking continuous black line with {len(path)} cells...")

        black_count = 0
        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            dr = r2 - r1
            dc = c2 - c1

            if dr != 0:  # 垂直方向（南北）
                x = self.origin_x + c1 * STEP + HALF_CELL + 1  # = c*4+2, 中心 x
                z1 = self.origin_z + min(r1, r2) * STEP + HALF_CELL + 1  # = min*4+2, 中心 z
                z2 = self.origin_z + max(r1, r2) * STEP + HALF_CELL + 1  # = max*4+2, 中心 z
                self._fill_floor(x, z1, x, z2, "minecraft:black_wool")
                black_count += (z2 - z1 + 1)
            else:  # 水平方向（东西）
                z = self.origin_z + r1 * STEP + HALF_CELL + 1  # = r*4+2, 中心 z
                x1 = self.origin_x + min(c1, c2) * STEP + HALF_CELL + 1  # = min*4+2, 中心 x
                x2 = self.origin_x + max(c1, c2) * STEP + HALF_CELL + 1  # = max*4+2, 中心 x
                self._fill_floor(x1, z, x2, z, "minecraft:black_wool")
                black_count += (x2 - x1 + 1)

        print(f"[MazeBuilder] Placed {black_count} black wool for continuous path line")

        # 出口 cell (0,0) 中心 3x3 红色羊毛（触发巡线停止）
        exit_r = 0
        exit_c = 0
        rx0 = self.origin_x + exit_c * STEP + 1
        rz0 = self.origin_z + exit_r * STEP + 1
        self._fill_floor(rx0, rz0, rx0 + 2, rz0 + 2, "minecraft:red_wool")
        print(f"[MazeBuilder] Red wool 3x3 at exit cell ({exit_r},{exit_c})")

    def get_cell_center(self, r, c):
        """获取 cell (r,c) 中心的世界坐标 (x, z)。"""
        cx = self.origin_x + c * STEP + HALF_CELL + 1.5  # = c*4 + 2.5
        cz = self.origin_z + r * STEP + HALF_CELL + 1.5  # = r*4 + 2.5
        return cx, cz



# 主入口
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Maze Solver — 在 Minecraft 中生成 {GRID_SIZE}x{GRID_SIZE} 迷宫并 A* 寻路 + 巡线导航"
    )
    parser.add_argument("--seed", type=int, default=42,
                        help="迷宫生成种子（默认 42，相同种子生成相同迷宫）")
    parser.add_argument("--car-id", type=int, default=1,
                        help="小车实体 agent ID（默认 1）")
    parser.add_argument("--build-only", action="store_true",
                        help="仅建造迷宫和标记路径，不启动巡线导航")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅打印路径信息，不执行任何方块操作（无需连接服务器）")
    parser.add_argument("--level", default="minecraft:overworld",
                        help="维度 ID（默认 minecraft:overworld）")
    parser.add_argument("--maze-y", type=int, default=None,
                        help="迷宫底层 Y 坐标（默认自动检测玩家位置）")
    parser.add_argument("--throttle", type=float, default=0.5,
                        help="巡线油门（默认 0.5）")
    args = parser.parse_args()

    # 连接
    print("[Main] Connecting to PyCraft...")
    from py_port import get_agent_manager

    mgr = get_agent_manager()

    # 获取玩家位置
    player_pos = mgr.get_player_pos(args.level)
    if player_pos is None:
        print("[Main] Cannot get player position. Make sure you're in-game.")
        return

    px, py, pz = player_pos
    maze_y = args.maze_y if args.maze_y is not None else int(py)
    print(f"[Main] Player position: ({px:.1f}, {py:.1f}, {pz:.1f})")
    print(f"[Main] Maze base Y: {maze_y}")

    # 生成迷宫
    print(f"[Main] Generating {GRID_SIZE}x{GRID_SIZE} maze with seed={args.seed}...")
    maze = MazeGenerator(seed=args.seed)

    # A* 寻路
    print("[Main] Running A* pathfinding...")
    finder = AStarPathfinder(maze)
    path = finder.find_path()
    if path is None:
        print("[Main] ERROR: No path found!")
        return
    print(f"[Main] Path found: {len(path)} cells")

    # 计算迷宫建造器（仅用于坐标计算，不实际建造方块）
    builder = MazeBuilder(mgr, args.level, px, maze_y, pz)
    entrance_cx, entrance_cz = builder.get_cell_center(GRID_SIZE - 1, GRID_SIZE - 1)
    exit_cx, exit_cz = builder.get_cell_center(0, 0)

    if not args.dry_run:
        # 建造迷宫（仅墙体和白色羊毛地面，不画路径线）
        print(f"[Main] Entrance center: ({entrance_cx:.1f}, {maze_y + 1:.1f}, {entrance_cz:.1f})")
        print(f"[Main] Exit center: ({exit_cx:.1f}, {maze_y + 1:.1f}, {exit_cz:.1f})")
        builder.build(maze)

        # 输出入口/出口坐标，供用户参考放置小车
        print(f"\n[Main] {'=' * 45}")
        print(f"[Main] 入口位置 (绿色羊毛): x={entrance_cx:.1f}, y={maze_y + 1:.1f}, z={entrance_cz:.1f}")
        print(f"[Main] 出口坐标: x={exit_cx:.1f}, y={maze_y + 1:.1f}, z={exit_cz:.1f}")
        print(f"[Main] 请在绿色羊毛处放置小车 (agent_id={args.car_id})")
        print(f"[Main] 放置好后按 Enter 绘制最优路径并开始巡线...")
        print(f"[Main] {'=' * 45}")
    else:
        # Dry-run: 仅打印路径信息
        print("[Main] Dry run mode — no blocks placed")
        print(f"\nPath ({len(path)} cells):")
        dir_names = {(-1, 0): 'N', (1, 0): 'S', (0, -1): 'W', (0, 1): 'E'}
        for i, (r, c) in enumerate(path):
            if i < len(path) - 1:
                dr = path[i + 1][0] - r
                dc = path[i + 1][1] - c
                direction = dir_names.get((dr, dc), '?')
                print(f"  {i}: ({r},{c}) → {direction}")
            else:
                print(f"  {i}: ({r},{c}) [终点]")
        dir_sequence = []
        for i in range(len(path) - 1):
            dr = path[i + 1][0] - path[i][0]
            dc = path[i + 1][1] - path[i][1]
            dir_sequence.append(dir_names.get((dr, dc), '?'))
        print(f"\nDirection sequence: {' → '.join(dir_sequence)}")
        print(f"Total steps: {len(path) - 1}")

    if args.build_only or args.dry_run:
        if args.build_only:
            print("[Main] Build-only mode, line following skipped.")
        return

    # 等待用户放置小车并按 Enter
    input()

    # 玩家确认后，在地面绘制连续黑线 + 绿色起点 + 红色终点
    print("[Main] Drawing path markers...")
    builder.mark_path(path)

    # 巡线导航
    print(f"\n[Main] Setting up line follower for car {args.car_id}...")
    from py_port.LineFollowController import LineFollowController

    ctrl = LineFollowController(args.car_id)
    car = mgr.get_agent(args.car_id)

    # 检测小车当前位置
    time.sleep(0.5)
    car_pos = car.get_position()
    print(f"[Main] Car detected at: ({car_pos[0]:.2f}, {car_pos[1]:.2f}, {car_pos[2]:.2f})")

    # 启动巡线（小车检测到绿色羊毛后会自动开始移动）
    print(f"[Main] Starting line follower with throttle={args.throttle}...")
    ctrl.start(throttle=args.throttle)

    # 监控循环：等待小车到达出口（红色羊毛区域）
    print(f"[Main] Monitoring until car reaches exit ({exit_cx:.1f}, {exit_cz:.1f})...")
    print("[Main] Press Ctrl+C to stop manually.")

    try:
        while True:
            time.sleep(0.5)
            pos = car.get_position()
            dx = pos[0] - exit_cx
            dz = pos[2] - exit_cz
            dist = math.sqrt(dx * dx + dz * dz)
            if dist < 2.0:
                print(f"[Main] Car reached exit area! Distance: {dist:.2f}")
                break
            # 可选：打印小车位置
            # print(f"[Main] Car at ({pos[0]:.1f}, {pos[2]:.1f}), "
            #       f"distance to exit: {dist:.2f}")
    except KeyboardInterrupt:
        print("\n[Main] Interrupted by user")
    finally:
        ctrl.stop()

    print(f"\n[Main] Maze solved! Car reached exit at ({exit_cx:.1f}, {exit_cz:.1f})")
    print("[Main] Done.")


if __name__ == "__main__":
    main()