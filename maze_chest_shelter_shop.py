import asyncio
import heapq
import math
from collections import deque
from typing import Optional

from pycraft import PyModClient


# 1. 迷宫配置
MAZE = [
    [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0],
    [0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 0, 1, 0],
    [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    [0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
]

PLAYER_START = (0, 0)
MAZE_EXIT_CELL = (9, 9)
ENTITY_Y_OFFSET = 0.0

# 玩家参数
PLAYER_MAZE_SPEED = 1.2
PLAYER_OUTSIDE_SPEED = 1.0

# Husk 参数
HUSK_MAX_HEALTH = 20.0
HUSK_HEALTH = 20.0
HUSK_MOVEMENT_SPEED = 0.5
HUSK_ATTACK_DAMAGE = 2.0
HUSK_FOLLOW_RANGE = 2048.0
HUSK_MAZE_SPEED = 0.45
HUSK_WORLD_NAVIGATION_SPEED = 1.0
HUSK_WORLD_REPATH_INTERVAL = 0.30
HUSK_ATTACK_RANGE = 2.50
HUSK_ATTACK_INTERVAL = 1.00

# 玩家先跑多久后，才在迷宫入口生成 Husk
HUSK_START_DELAY = 3

# 宝箱奖励
CHEST_ITEM = "minecraft:iron_ingot"
CHEST_ITEM_COUNT = 1
CHEST_SLOT = 0

# 破门时间
DOOR_BREAK_TIME = 10.0

# 玩家到屋内、Husk 进入屋内后继续测试多久
CHASE_DURATION_AFTER_PLAYER_FINISHES = 60.0


# 2. 庇护所配置
HOUSE_WIDTH = 9
HOUSE_LENGTH = 9
WALL_HEIGHT = 4
HOUSE_GAP_FROM_MAZE = 8

STONE_BLOCK = "minecraft:stone"
FLOOR_BLOCK = "minecraft:smooth_stone"
AIR_BLOCK = "minecraft:air"
GLASS_BLOCK = "minecraft:glass"

# 暂时用两格高橡木木板模拟门
DOOR_BLOCK = "minecraft:oak_planks"


def distance_3d(a, b) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
        + (a[2] - b[2]) ** 2
    )


def maze_cell_to_world(cell, base_x: int, entity_y: float, base_z: int):
    row, col = cell
    return (
        base_x + row + 0.5,
        entity_y,
        base_z + col + 0.5,
    )


def world_to_maze_cell(position, base_x: int, base_z: int):
    x, _, z = position
    return (
        int(math.floor(x - base_x)),
        int(math.floor(z - base_z)),
    )


def is_inside_maze(position, base_x: int, base_z: int, maze) -> bool:
    row, col = world_to_maze_cell(position, base_x, base_z)
    return (
        0 <= row < len(maze)
        and 0 <= col < len(maze[0])
    )


def is_walkable_cell(maze, cell) -> bool:
    row, col = cell
    return (
        0 <= row < len(maze)
        and 0 <= col < len(maze[0])
        and maze[row][col] == 0
    )


def nearest_walkable_cell(maze, start_cell):
    if is_walkable_cell(maze, start_cell):
        return start_cell

    rows = len(maze)
    cols = len(maze[0])
    queue = deque([start_cell])
    visited = {start_cell}

    while queue:
        row, col = queue.popleft()

        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = row + dr, col + dc

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            neighbor = (nr, nc)

            if neighbor in visited:
                continue

            if maze[nr][nc] == 0:
                return neighbor

            visited.add(neighbor)
            queue.append(neighbor)

    return None


def split_line_into_points(start, target, *, step_length=1.0):
    total_distance = distance_3d(start, target)

    if total_distance <= step_length:
        return [target]

    count = math.ceil(total_distance / step_length)
    points = []

    for index in range(1, count + 1):
        ratio = index / count
        points.append(
            (
                start[0] + (target[0] - start[0]) * ratio,
                start[1] + (target[1] - start[1]) * ratio,
                start[2] + (target[2] - start[2]) * ratio,
            )
        )

    return points


async def move_to_single_point_and_wait(
    entity,
    target,
    *,
    speed,
    entity_name,
    arrival_threshold=0.45,
    poll_interval=0.10,
    timeout=4.0,
    stuck_timeout=1.8,
):
    start_pos = await entity.get_pos()

    if distance_3d(start_pos, target) <= arrival_threshold:
        return True

    await entity.move_to(
        target[0],
        target[1],
        target[2],
        speed=speed,
    )

    loop = asyncio.get_running_loop()
    start_time = loop.time()
    last_pos = start_pos
    still_time = 0.0

    while True:
        await asyncio.sleep(poll_interval)

        current_pos = await entity.get_pos()
        remaining = distance_3d(current_pos, target)

        print(
            f"[{entity_name}] "
            f"pos=({current_pos[0]:.2f}, {current_pos[1]:.2f}, {current_pos[2]:.2f}), "
            f"target=({target[0]:.2f}, {target[1]:.2f}, {target[2]:.2f}), "
            f"remaining={remaining:.2f}"
        )

        if remaining <= arrival_threshold:
            return True

        moved = distance_3d(current_pos, last_pos)

        if moved < 0.025:
            still_time += poll_interval
        else:
            still_time = 0.0

        if still_time >= stuck_timeout:
            print(f"[{entity_name}] movement appears stuck")
            return False

        if loop.time() - start_time >= timeout:
            print(f"[{entity_name}] movement timeout")
            return False

        last_pos = current_pos


async def move_to_and_wait(
    entity,
    target,
    *,
    speed,
    entity_name,
    step_length=0.8,
    arrival_threshold=0.45,
    poll_interval=0.10,
    timeout=4.0,
    stuck_timeout=1.8,
    point_sleep=0.05,
):
    """把较长直线拆成多个短节点，使用move_to()逐点移动。"""
    start_pos = await entity.get_pos()
    points = split_line_into_points(
        start_pos,
        target,
        step_length=step_length,
    )

    for index, point in enumerate(points, start=1):
        success = await move_to_single_point_and_wait(
            entity,
            point,
            speed=speed,
            entity_name=entity_name,
            arrival_threshold=arrival_threshold,
            poll_interval=poll_interval,
            timeout=timeout,
            stuck_timeout=stuck_timeout,
        )

        if not success:
            return False

        await asyncio.sleep(point_sleep)

    return True


# A* 算法寻路
class AStar:
    def __init__(self, maze):
        self.maze = maze

    @staticmethod
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, cell):
        row, col = cell
        result = []

        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = (row + dr, col + dc)

            if is_walkable_cell(self.maze, candidate):
                result.append(candidate)

        return result

    def find_path(self, start, goal):
        start = tuple(start)
        goal = tuple(goal)

        if not is_walkable_cell(self.maze, start):
            return []

        if not is_walkable_cell(self.maze, goal):
            return []

        open_heap = []
        counter = 0
        heapq.heappush(
            open_heap,
            (self.heuristic(start, goal), counter, start),
        )

        came_from = {}
        g_score = {start: 0}
        closed = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)

            if current in closed:
                continue

            if current == goal:
                path = [current]

                while current in came_from:
                    current = came_from[current]
                    path.append(current)

                return path[::-1]

            closed.add(current)

            for neighbor in self.get_neighbors(current):
                tentative_g = g_score[current] + 1

                if tentative_g >= g_score.get(neighbor, math.inf):
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                counter += 1

                heapq.heappush(
                    open_heap,
                    (
                        tentative_g + self.heuristic(neighbor, goal),
                        counter,
                        neighbor,
                    ),
                )

        return []



def choose_chest_branch(astar, maze, optimal_path):
    """
    选择一个不在最优路径上的死胡同作为宝箱位置。
    """
    optimal_set = set(optimal_path)
    candidates = []

    for row in range(len(maze)):
        for col in range(len(maze[0])):
            cell = (row, col)

            if not is_walkable_cell(maze, cell) or cell in optimal_set:
                continue

            neighbors = astar.get_neighbors(cell)

            # 优先选死胡同，避免宝箱挡住其他必经路线
            if len(neighbors) != 1:
                continue

            access_cell = neighbors[0]
            path_to_access = astar.find_path(PLAYER_START, access_cell)
            path_from_access_to_exit = astar.find_path(access_cell, MAZE_EXIT_CELL)

            if not path_to_access or not path_from_access_to_exit:
                continue

            detour_length = (
                len(path_to_access)
                + len(path_from_access_to_exit)
                - len(optimal_path)
            )
            candidates.append(
                (detour_length, cell, access_cell, path_to_access, path_from_access_to_exit)
            )

    if not candidates:
        raise RuntimeError("No suitable off-optimal-path dead end for chest")

    # 这里选择绕路代价最大的支线
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, chest_cell, access_cell, path_to_access, path_from_access_to_exit = candidates[0]

    return {
        "chest_cell": chest_cell,
        "access_cell": access_cell,
        "path_to_access": path_to_access,
        "path_from_access_to_exit": path_from_access_to_exit,
    }


async def place_reward_chest(
    level,
    *,
    base_x: int,
    base_y: int,
    base_z: int,
    chest_cell,
):
    row, col = chest_cell
    chest_pos = (
        base_x + row,
        base_y,
        base_z + col,
    )

    await level.set_block(*chest_pos, "minecraft:chest")
    await level.set_container_item(
        *chest_pos,
        slot=CHEST_SLOT,
        item=CHEST_ITEM,
        count=CHEST_ITEM_COUNT,
    )

    print(
        f"[Chest] placed at maze cell={chest_cell}, world={chest_pos}, "
        f"item={CHEST_ITEM} x{CHEST_ITEM_COUNT}"
    )
    return chest_pos


async def close_maze_entrance(level, base_x: int, base_y: int, base_z: int):
    """
    Husk 进入迷宫后封闭入口，防止原生导航从入口离开迷宫并绕外墙。
    """
    entrance_x = base_x + PLAYER_START[0]
    entrance_z = base_z - 1

    await level.set_blocks(
        entrance_x,
        base_y,
        entrance_z,
        entrance_x,
        base_y + 2,
        entrance_z,
        STONE_BLOCK,
    )


# 建造迷宫、庇护所
async def draw_maze(level, maze, base_x: int, base_y: int, base_z: int):
    rows = len(maze)
    cols = len(maze[0])

    await level.set_blocks(
        base_x - 1,
        base_y - 2,
        base_z - 1,
        base_x + rows,
        base_y + 5,
        base_z + cols + 3,
        AIR_BLOCK,
    )

    await level.set_blocks(
        base_x - 1,
        base_y - 1,
        base_z - 1,
        base_x + rows,
        base_y - 1,
        base_z + cols + 3,
        FLOOR_BLOCK,
    )

    # 四周外墙
    await level.set_blocks(
        base_x - 1, base_y, base_z - 1,
        base_x + rows, base_y + 2, base_z - 1,
        STONE_BLOCK,
    )
    await level.set_blocks(
        base_x - 1, base_y, base_z + cols,
        base_x + rows, base_y + 2, base_z + cols,
        STONE_BLOCK,
    )
    await level.set_blocks(
        base_x - 1, base_y, base_z,
        base_x - 1, base_y + 2, base_z + cols,
        STONE_BLOCK,
    )
    await level.set_blocks(
        base_x + rows, base_y, base_z,
        base_x + rows, base_y + 2, base_z + cols,
        STONE_BLOCK,
    )

    # 起点和出口
    await level.set_blocks(
        base_x + PLAYER_START[0],
        base_y,
        base_z - 1,
        base_x + PLAYER_START[0],
        base_y + 2,
        base_z - 1,
        AIR_BLOCK,
    )
    await level.set_blocks(
        base_x + MAZE_EXIT_CELL[0],
        base_y,
        base_z + cols,
        base_x + MAZE_EXIT_CELL[0],
        base_y + 2,
        base_z + cols,
        AIR_BLOCK,
    )

    # 内部墙体
    for row in range(rows):
        for col in range(cols):
            if maze[row][col] == 1:
                await level.set_blocks(
                    base_x + row,
                    base_y,
                    base_z + col,
                    base_x + row,
                    base_y + 2,
                    base_z + col,
                    STONE_BLOCK,
                )


async def build_shelter_and_corridor(
    level,
    *,
    base_x: int,
    base_y: int,
    base_z: int,
):
    """在迷宫出口前方建造庇护所，并返回所有关键坐标。"""
    cols = len(MAZE[0])

    # 让门的中心与迷宫出口基本对齐
    house_x = base_x + MAZE_EXIT_CELL[0] - HOUSE_WIDTH // 2
    house_y = base_y
    house_z = base_z + cols + HOUSE_GAP_FROM_MAZE

    x_min = house_x
    x_max = house_x + HOUSE_WIDTH - 1
    z_min = house_z
    z_max = house_z + HOUSE_LENGTH - 1

    floor_y = house_y - 1
    wall_bottom_y = house_y
    wall_top_y = house_y + WALL_HEIGHT

    door_x = house_x + HOUSE_WIDTH // 2
    door_y = house_y
    door_z = house_z

    door_front = (
        door_x + 0.5,
        float(house_y) + ENTITY_Y_OFFSET,
        door_z - 0.5,
    )
    inside_target = (
        door_x + 0.5,
        float(house_y) + ENTITY_Y_OFFSET,
        door_z + 2.5,
    )

    # 清空房屋区域
    await level.set_blocks(
        x_min,
        wall_bottom_y,
        z_min,
        x_max,
        wall_top_y + 2,
        z_max,
        AIR_BLOCK,
    )

    # 地板
    await level.set_blocks(
        x_min,
        floor_y,
        z_min,
        x_max,
        floor_y,
        z_max,
        STONE_BLOCK,
    )

    # 四面墙
    await level.set_blocks(
        x_min, wall_bottom_y, z_min,
        x_max, wall_top_y, z_min,
        STONE_BLOCK,
    )
    await level.set_blocks(
        x_min, wall_bottom_y, z_max,
        x_max, wall_top_y, z_max,
        STONE_BLOCK,
    )
    await level.set_blocks(
        x_min, wall_bottom_y, z_min,
        x_min, wall_top_y, z_max,
        STONE_BLOCK,
    )
    await level.set_blocks(
        x_max, wall_bottom_y, z_min,
        x_max, wall_top_y, z_max,
        STONE_BLOCK,
    )

    # 商店触发:/pycraft shop
    ai_shop_id = await level.spawn_algorithm(int((x_min + x_max)/2), wall_bottom_y + 1, int((z_min + z_max)/2))

    # 门洞初始保持打开
    await level.set_block(door_x, door_y, door_z, AIR_BLOCK)
    await level.set_block(door_x, door_y + 1, door_z, AIR_BLOCK)

    # 窗户
    window_y = house_y + 1
    window_positions = [
        # 南墙，门旁边四扇
        (door_x - 2, window_y, z_min),
        (door_x - 1, window_y, z_min),
        (door_x + 1, window_y, z_min),
        (door_x + 2, window_y, z_min),
        # 北墙
        (house_x + 2, window_y, z_max),
        (house_x + HOUSE_WIDTH - 3, window_y, z_max),
        # 西墙
        (x_min, window_y, house_z + 2),
        (x_min, window_y, house_z + HOUSE_LENGTH - 3),
        # 东墙
        (x_max, window_y, house_z + 2),
        (x_max, window_y, house_z + HOUSE_LENGTH - 3),
    ]

    for wx, wy, wz in window_positions:
        await level.set_block(wx, wy, wz, GLASS_BLOCK)

    # 建造迷宫出口到庇护所门前的平整通道
    maze_exit_world = maze_cell_to_world(
        MAZE_EXIT_CELL,
        base_x,
        float(base_y) + ENTITY_Y_OFFSET,
        base_z,
    )

    corridor_x_min = min(int(math.floor(maze_exit_world[0])), door_x) - 1
    corridor_x_max = max(int(math.floor(maze_exit_world[0])), door_x) + 1
    corridor_z_min = base_z + cols
    corridor_z_max = door_z - 1

    await level.set_blocks(
        corridor_x_min,
        base_y,
        corridor_z_min,
        corridor_x_max,
        base_y + 2,
        corridor_z_max,
        AIR_BLOCK,
    )
    await level.set_blocks(
        corridor_x_min,
        base_y - 1,
        corridor_z_min,
        corridor_x_max,
        base_y - 1,
        corridor_z_max,
        FLOOR_BLOCK,
    )

    return {
        "house_x": house_x,
        "house_y": house_y,
        "house_z": house_z,
        "x_min": x_min,
        "x_max": x_max,
        "z_min": z_min,
        "z_max": z_max,
        "door_x": door_x,
        "door_y": door_y,
        "door_z": door_z,
        "door_front": door_front,
        "inside_target": inside_target,
        "ai_shop_id": ai_shop_id,
    }


async def mark_path(level, path, base_x: int, base_y: int, base_z: int):
    for row, col in path:
        await level.set_block(
            base_x + row,
            base_y - 1,
            base_z + col,
            "minecraft:gold_block",
        )


async def close_shelter_door(level, shelter):
    await level.set_block(
        shelter["door_x"],
        shelter["door_y"],
        shelter["door_z"],
        DOOR_BLOCK,
    )
    await level.set_block(
        shelter["door_x"],
        shelter["door_y"] + 1,
        shelter["door_z"],
        DOOR_BLOCK,
    )
    print("[Shelter] two-block wooden barrier closed")


async def destroy_shelter_door(level, shelter):
    await level.set_block(
        shelter["door_x"],
        shelter["door_y"],
        shelter["door_z"],
        AIR_BLOCK,
    )
    await level.set_block(
        shelter["door_x"],
        shelter["door_y"] + 1,
        shelter["door_z"],
        AIR_BLOCK,
    )
    print("[Shelter] wooden barrier destroyed")



# Husk追逐控制
class HuskChaseController:
    def __init__(
        self,
        *,
        husk,
        player,
        level,
        astar,
        maze,
        base_x,
        base_y,
        base_z,
        shelter,
        door_closed_event: asyncio.Event,
    ):
        self.husk = husk
        self.player = player
        self.level = level
        self.astar = astar
        self.maze = maze
        self.base_x = base_x
        self.base_y = base_y
        self.entity_y = float(base_y) + ENTITY_Y_OFFSET
        self.base_z = base_z
        self.shelter = shelter
        self.door_closed_event = door_closed_event

        self.running = False
        self.last_attack_time = 0.0
        self.native_navigation_active = False
        self.door_broken = False
        self.breaking_door = False

    async def stop_native_navigation(self):
        if not self.native_navigation_active:
            return

        try:
            await self.husk.stop_navigation()
        except Exception as error:
            print(f"[Husk] stop_navigation failed: {error}")
        finally:
            self.native_navigation_active = False

    async def try_attack(self) -> bool:
        husk_pos = await self.husk.get_pos()
        player_pos = await self.player.get_pos()

        if distance_3d(husk_pos, player_pos) > HUSK_ATTACK_RANGE:
            return False

        await self.stop_native_navigation()
        now = asyncio.get_running_loop().time()

        if now - self.last_attack_time < HUSK_ATTACK_INTERVAL:
            return True

        result = await self.husk.attack(self.player)
        print(
            "[Husk attack] "
            f"hit={result.get('hit')}, "
            f"damage={result.get('damage_dealt')}, "
            f"target_health={result.get('target_health')}"
        )
        self.last_attack_time = now
        return True

    async def move_one_astar_step(self, target_cell) -> bool:
        await self.stop_native_navigation()

        husk_pos = await self.husk.get_pos()
        husk_cell = nearest_walkable_cell(
            self.maze,
            world_to_maze_cell(husk_pos, self.base_x, self.base_z),
        )
        target_cell = nearest_walkable_cell(self.maze, target_cell)

        if husk_cell is None or target_cell is None:
            return False

        path = self.astar.find_path(husk_cell, target_cell)

        if not path:
            print(f"[Husk A*] no path {husk_cell} -> {target_cell}")
            return False

        if len(path) == 1:
            return True

        next_cell = path[1]
        next_world = maze_cell_to_world(
            next_cell,
            self.base_x,
            self.entity_y,
            self.base_z,
        )

        print(
            f"[Husk A*] {husk_cell} -> {next_cell}, "
            f"target={target_cell}, path_length={len(path)}"
        )

        return await move_to_and_wait(
            self.husk,
            next_world,
            speed=HUSK_MAZE_SPEED,
            entity_name="Husk",
            step_length=0.7,
            arrival_threshold=0.35,
            timeout=4.0,
            stuck_timeout=2.0,
        )

    async def leave_maze(self):
        cols = len(self.maze[0])
        outside_point = (
            self.base_x + MAZE_EXIT_CELL[0] + 0.5,
            self.entity_y,
            self.base_z + cols + 1.5,
        )

        await move_to_and_wait(
            self.husk,
            outside_point,
            speed=HUSK_MAZE_SPEED,
            entity_name="Husk",
            step_length=0.8,
            arrival_threshold=0.60,
            timeout=5.0,
            stuck_timeout=2.2,
        )

    async def break_door_sequence(self):
        if self.breaking_door or self.door_broken:
            return

        self.breaking_door = True
        await self.stop_native_navigation()

        print("[Husk] moving to shelter door")

        reached = await move_to_and_wait(
            self.husk,
            self.shelter["door_front"],
            speed=HUSK_WORLD_NAVIGATION_SPEED,
            entity_name="Husk-Door",
            step_length=0.8,
            arrival_threshold=0.30,
            timeout=5.0,
            stuck_timeout=2.5,
        )

        if not reached:
            print("[Husk] failed to reach shelter door; retrying later")
            self.breaking_door = False
            return

        try:
            await self.husk.stop_navigation()
        except Exception:
            pass

        door_blocks = [
            (
                self.shelter["door_x"],
                self.shelter["door_y"],
                self.shelter["door_z"],
            ),
            (
                self.shelter["door_x"],
                self.shelter["door_y"] + 1,
                self.shelter["door_z"],
            ),
        ]

        print(
            f"[Husk] attacking both door blocks for "
            f"{DOOR_BREAK_TIME:.1f}s"
        )

        try:
            result = await self.husk.break_blocks(
                door_blocks,
                break_time=DOOR_BREAK_TIME,
            )
            print(
                "[Breaking door] task started: "
                f"blocks={result.get('block_count')}, "
                f"ticks={result.get('break_ticks')}"
            )
        except Exception as error:
            print(f"[Husk] failed to start door-breaking task: {error}")
            self.breaking_door = False
            return

        # break_blocks() only confirms that the task started. Keep this chase
        # coroutine at the doorway until the server has removed both blocks.
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        last_reported_second = -1
        break_timeout = DOOR_BREAK_TIME + 2.0

        while True:
            block_states = await asyncio.gather(
                *(
                    self.level.get_block(x, y, z)
                    for x, y, z in door_blocks
                )
            )

            if all(state == AIR_BLOCK for state in block_states):
                self.door_broken = True
                print("[Shelter] both door blocks were broken by Husk")
                break

            elapsed = loop.time() - started_at
            elapsed_second = int(elapsed)
            if elapsed_second != last_reported_second:
                last_reported_second = elapsed_second
                progress = min(100.0, elapsed / DOOR_BREAK_TIME * 100.0)
                print(
                    f"[Breaking door] {elapsed:.1f}/{DOOR_BREAK_TIME:.1f}s "
                    f"({progress:.0f}%), states={block_states}"
                )

            if elapsed >= break_timeout:
                print(
                    "[Husk] door-breaking task did not finish; "
                    "it will be retried"
                )
                self.breaking_door = False
                return

            await asyncio.sleep(0.20)

        print("[Husk] entering shelter")
        await move_to_and_wait(
            self.husk,
            self.shelter["inside_target"],
            speed=HUSK_WORLD_NAVIGATION_SPEED,
            entity_name="Husk",
            step_length=0.7,
            arrival_threshold=0.75,
            timeout=5.0,
            stuck_timeout=2.5,
        )

        self.breaking_door = False

    async def run(self):
        self.running = True

        try:
            while self.running:
                husk_pos = await self.husk.get_pos()
                player_pos = await self.player.get_pos()

                print(
                    f"Husk-player distance={distance_3d(husk_pos, player_pos):.2f}"
                )

                if await self.try_attack():
                    await asyncio.sleep(0.10)
                    continue

                husk_inside_maze = is_inside_maze(
                    husk_pos,
                    self.base_x,
                    self.base_z,
                    self.maze,
                )

                if husk_inside_maze:
                    husk_cell = nearest_walkable_cell(
                        self.maze,
                        world_to_maze_cell(husk_pos, self.base_x, self.base_z),
                    )


                    player_inside_maze = is_inside_maze(
                        player_pos,
                        self.base_x,
                        self.base_z,
                        self.maze,
                    )

                    if player_inside_maze:
                        target_cell = nearest_walkable_cell(
                            self.maze,
                            world_to_maze_cell(
                                player_pos,
                                self.base_x,
                                self.base_z,
                            ),
                        )
                    else:
                        target_cell = MAZE_EXIT_CELL

                    if (
                        not player_inside_maze
                        and husk_cell == MAZE_EXIT_CELL
                    ):
                        await self.leave_maze()
                    elif target_cell is not None:
                        await self.move_one_astar_step(target_cell)

                    continue

                # 玩家已经进屋并关门时，固定去门前破门
                if self.door_closed_event.is_set() and not self.door_broken:
                    await self.break_door_sequence()
                    continue

                # 迷宫外、门尚未关闭或已经破坏：原生导航追踪玩家
                result = await self.husk.navigate_to_entity(
                    self.player,
                    speed=HUSK_WORLD_NAVIGATION_SPEED,
                )
                self.native_navigation_active = True
                await asyncio.sleep(HUSK_WORLD_REPATH_INTERVAL)

        except asyncio.CancelledError:
            raise
        finally:
            await self.stop_native_navigation()

    def stop(self):
        self.running = False



async def main():
    client = PyModClient(host="127.0.0.1", port=8086)

    player_task: Optional[asyncio.Task] = None
    husk_task: Optional[asyncio.Task] = None
    tracker: Optional[HuskChaseController] = None

    door_closed_event = asyncio.Event()

    try:
        await client.connect()
        level = client.overworld()

        players = await level.get_players()
        if not players:
            raise RuntimeError("World has no players")

        player = players[0]
        # await player.set_overhead_view(enabled=True, height=10)
        await player.set_perspective(0)

        px, py, pz = await player.get_pos()
        base_x = int(math.floor(px))
        base_y = int(math.floor(py))
        base_z = int(math.floor(pz))
        entity_y = float(base_y) + ENTITY_Y_OFFSET

        print(f"Initial player position=({px:.2f}, {py:.2f}, {pz:.2f})")

        # 生成迷宫与庇护所
        await draw_maze(level, MAZE, base_x, base_y, base_z)
        shelter = await build_shelter_and_corridor(
            level,
            base_x=base_x,
            base_y=base_y,
            base_z=base_z,
        )

        astar = AStar(MAZE)
        optimal_path = astar.find_path(PLAYER_START, MAZE_EXIT_CELL)

        if not optimal_path:
            raise RuntimeError("Maze start and exit are not connected")

        # 黄金方块只标记不开宝箱的最优路线。
        await mark_path(level, optimal_path, base_x, base_y, base_z)

        # 选择不经过最优路线的死胡同，并放入装有铁块的宝箱。
        chest_plan = choose_chest_branch(astar, MAZE, optimal_path)
        chest_pos = await place_reward_chest(
            level,
            base_x=base_x,
            base_y=base_y,
            base_z=base_z,
            chest_cell=chest_plan["chest_cell"],
        )

        print(
            f"[Planner] original optimal length={len(optimal_path)}; "
            f"chest cell={chest_plan['chest_cell']}; "
            f"access cell={chest_plan['access_cell']}"
        )

        # 玩家传送到迷宫起点
        player_start_world = maze_cell_to_world(
            PLAYER_START,
            base_x,
            entity_y,
            base_z,
        )
        await player.teleport(*player_start_world)

        async def run_player_route():
            async def follow_grid_path(path, phase_name):
                for index, cell in enumerate(path[1:], start=1):
                    target = maze_cell_to_world(cell, base_x, entity_y, base_z)
                    print(
                        f"[Player {phase_name} {index}/{len(path) - 1}] "
                        f"cell={cell}"
                    )

                    success = await move_to_and_wait(
                        player,
                        target,
                        speed=PLAYER_MAZE_SPEED,
                        entity_name="Player",
                        step_length=0.8,
                        arrival_threshold=0.35,
                        timeout=4.5,
                        stuck_timeout=2.0,
                    )

                    if not success:
                        success = await move_to_and_wait(
                            player,
                            target,
                            speed=PLAYER_MAZE_SPEED * 0.8,
                            entity_name="Player",
                            step_length=0.6,
                            arrival_threshold=0.40,
                            timeout=5.5,
                            stuck_timeout=2.5,
                        )

                    if not success:
                        raise RuntimeError(
                            f"Player cannot reach maze cell {cell}"
                        )

            # 第一阶段：重新规划到宝箱旁边
            await follow_grid_path(
                chest_plan["path_to_access"],
                "TO_CHEST",
            )

            print("[Player] reached chest branch; checking chest contents")
            items = await level.get_container_items(*chest_pos)
            print(f"[Chest contents] {items}")

            reward = next(
                (
                    item for item in items
                    if item.get("slot") == CHEST_SLOT
                    and item.get("item") == CHEST_ITEM
                ),
                None,
            )

            if reward is None:
                raise RuntimeError(
                    f"Expected {CHEST_ITEM} in chest slot {CHEST_SLOT}, got {items}"
                )

            take_count = min(CHEST_ITEM_COUNT, int(reward["count"]))
            take_result = await level.take_container_item(
                player.entity_id,
                *chest_pos,
                CHEST_SLOT,
                take_count,
            )
            print(f"[Player] took reward from chest: {take_result}")

            # 第二阶段：拿到铁块后，从宝箱支线重新规划至迷宫出口。
            await follow_grid_path(
                chest_plan["path_from_access_to_exit"],
                "CHEST_TO_EXIT",
            )

            print("[Player] running from maze exit to shelter")

            if not await move_to_and_wait(
                player,
                shelter["door_front"],
                speed=PLAYER_OUTSIDE_SPEED,
                entity_name="Player",
                step_length=0.9,
                arrival_threshold=0.55,
                timeout=5.0,
                stuck_timeout=2.2,
            ):
                raise RuntimeError("Player cannot reach shelter door")

            if not await move_to_and_wait(
                player,
                shelter["inside_target"],
                speed=PLAYER_OUTSIDE_SPEED,
                entity_name="Player",
                step_length=0.7,
                arrival_threshold=0.65,
                timeout=5.0,
                stuck_timeout=2.2,
            ):
                raise RuntimeError("Player cannot enter shelter")

            await close_shelter_door(level, shelter)
            door_closed_event.set()
            print("[Player] inside shelter; door closed")

        player_task = asyncio.create_task(run_player_route())

        # 玩家先跑一段时间，再在同一个迷宫入口生成Husk
        await asyncio.sleep(HUSK_START_DELAY)

        husk_start_world = maze_cell_to_world(
            PLAYER_START,
            base_x,
            entity_y,
            base_z,
        )
        husk = await level.spawn_entity("husk", *husk_start_world)
        print(f"[Husk] spawned at maze entrance after {HUSK_START_DELAY:.1f}s")

        # 封闭 Husk 身后的入口，避免其使用原生导航绕到迷宫外圈。
        await close_maze_entrance(level, base_x, base_y, base_z)

        await husk.set_attributes(
            max_health=HUSK_MAX_HEALTH,
            health=HUSK_HEALTH,
            movement_speed=HUSK_MOVEMENT_SPEED,
            attack_damage=HUSK_ATTACK_DAMAGE,
            follow_range=HUSK_FOLLOW_RANGE,
        )

        tracker = HuskChaseController(
            husk=husk,
            player=player,
            level=level,
            astar=astar,
            maze=MAZE,
            base_x=base_x,
            base_y=base_y,
            base_z=base_z,
            shelter=shelter,
            door_closed_event=door_closed_event,
        )
        husk_task = asyncio.create_task(tracker.run())

        await player_task
        print("[Main] player route completed; Husk continues chasing")

        await asyncio.sleep(CHASE_DURATION_AFTER_PLAYER_FINISHES)

    except Exception as error:
        print(f"[Main error] {type(error).__name__}: {error}")
        raise

    finally:
        if tracker is not None:
            tracker.stop()

        if husk_task is not None and not husk_task.done():
            husk_task.cancel()
            try:
                await husk_task
            except asyncio.CancelledError:
                pass

        if player_task is not None and not player_task.done():
            player_task.cancel()
            try:
                await player_task
            except asyncio.CancelledError:
                pass

        await client.close()
        print("Program finished")


if __name__ == "__main__":
    asyncio.run(main())
