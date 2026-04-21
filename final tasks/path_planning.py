import asyncio
import heapq
import json
from collections import deque
from pycraft import PyModClient
from env import load_env
from pycraft.api.uav import UavEntity

ASSIGN_PATH = "./final tasks/assignment.json"
GRID_SIZE = 256
OFFSET = GRID_SIZE // 2
FLY_HEIGHT = 3

FREE = 0
BLOCK = 1

class AStar:
    def __init__(self, maze):
        self.maze = maze
        self.height = len(maze)
        self.width = len(maze[0])

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, pos):
        x, y = pos
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.height and 0 <= ny < self.width:
                if self.maze[nx][ny] == FREE:
                    neighbors.append((nx, ny))
        return neighbors

    def find_path(self, start, end):
        start = tuple(start)
        end = tuple(end)
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        closed_set = set()
        while open_set:
            current_f, current = heapq.heappop(open_set)
            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            if current in closed_set:
                continue
            closed_set.add(current)
            for neighbor in self.get_neighbors(current):
                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self.heuristic(neighbor, end)
                    heapq.heappush(open_set, (f, neighbor))
        return []


# 坐标转换
def to_grid(x, z):
    return int(x) + OFFSET, int(z) + OFFSET

def to_world(gx, gz):
    return gx - OFFSET, gz - OFFSET

# 找最近可达点，让无人机到达房子附近
def find_nearest_free(maze, start):
    queue = deque([start])
    visited = set([start])
    while queue:
        x, y = queue.popleft()
        if maze[x][y] == FREE:
            return (x, y)
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited:
                if 0 <= nx < len(maze) and 0 <= ny < len(maze[0]):
                    queue.append((nx, ny))
                    visited.add((nx, ny))
    return start

# 构建maze
def build_maze(env):
    maze = [[FREE for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    # 房屋
    for x, y, z in env["houses"]:
        gx, gz = to_grid(x, z)
        for dx in range(-2, 3): 
            for dz in range(-2, 3):
                nx, nz = gx + dx, gz + dz
                if 0 <= nx < GRID_SIZE and 0 <= nz < GRID_SIZE:
                    maze[nx][nz] = BLOCK
    # 树
    for x, y, z in env["obstacles"]:
        gx, gz = to_grid(x, z)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                nx, nz = gx + dx, gz + dz
                if 0 <= nx < GRID_SIZE and 0 <= nz < GRID_SIZE:
                    maze[nx][nz] = BLOCK
    return maze

async def mark_target(level, x, y, z):
    """
    在目标房屋上方放标记
    """
    height = 5
    # 柱子
    await level.set_blocks(x, y+1, z, x, y+height, z, "minecraft:gold_block")
    # 顶部标志
    await level.set_block(x, y+height+1, z, "minecraft:redstone_block")

# 读取任务
def load_tasks():
    with open(ASSIGN_PATH, "r") as f:
        return json.load(f)["tasks"]


async def main():
    client = PyModClient()
    await client.connect()
    level = client.overworld()
    players = await level.get_players()
    player = players[0]
    base_x, base_y, base_z = await player.get_pos()
    env = load_env()
    maze = build_maze(env)
    astar = AStar(maze)
    tasks = load_tasks()
    print("开始路径规划...")
    for task in tasks:
        start = task["start"]
        goal = task["goal"]
        await mark_target(level, int(goal[0]), 0 + base_y, int(goal[1]))

        # 转网格
        start_g = to_grid(start[0], start[1])
        goal_g = to_grid(goal[0], goal[1])
        start_g = find_nearest_free(maze, start_g)
        goal_g = find_nearest_free(maze, goal_g)
        print("start:", start_g, "goal:", goal_g)

        path = astar.find_path(start_g, goal_g)
        if not path:
            print("路径失败:", task)
            continue
        print(f"UAV {task['uav_id']} 路径长度:", len(path))
        world_path = [to_world(x, y) for x, y in path]

        # 显示路径
        draw_path = [(x, base_y + FLY_HEIGHT, z) for x, z in world_path]
        await level.draw_path(draw_path, duration=20000)
        # 飞行
        uav = UavEntity(client, task["uav_id"])
        for x, z in world_path:
            await uav.set_target(x, base_y + FLY_HEIGHT, z)
            await asyncio.sleep(0.05)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())