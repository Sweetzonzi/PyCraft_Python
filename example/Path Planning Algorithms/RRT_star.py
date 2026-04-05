import asyncio
import heapq
import time
import random
import math
import copy

from pycraft import PyModClient

def create_maze():
    return [[0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 1, 1, 0, 1, 1, 0, 0],
            [0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
            [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            [0, 1, 0, 0, 1, 0, 0, 0, 1, 0]]

async def draw_maze(level, maze, base_x, base_y, base_z):
    rows = len(maze)
    cols = len(maze[0])
    stone = "minecraft:stone"
    air = "minecraft:air"
    # 清空区域
    await level.set_blocks(
        base_x - 1, base_y - 3, base_z - 1,
        base_x + rows + 1, base_y + 5, base_z + cols + 1,
        air
    )
    # 外墙
    await level.set_blocks(base_x-1, base_y-3, base_z-1, base_x+rows, base_y, base_z-1, stone)
    await level.set_blocks(base_x-1, base_y-3, base_z+cols, base_x+rows, base_y, base_z+cols, stone)
    await level.set_blocks(base_x-1, base_y-3, base_z, base_x-1, base_y, base_z+cols, stone)
    await level.set_blocks(base_x+rows, base_y-3, base_z, base_x+rows, base_y, base_z+cols, stone)
    for r in range(rows):
        for c in range(cols):
            if maze[r][c] == 1:
                await level.set_blocks(
                    base_x + r, base_y - 3, base_z + c,
                    base_x + r, base_y, base_z + c,
                    stone
                )

def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def get_nearest(tree, point):
    return min(tree.keys(), key=lambda n: distance(n, point))

def steer(from_node, to_node):
    r1, c1 = from_node
    r2, c2 = to_node
    dr = r2 - r1
    dc = c2 - c1
    if abs(dr) > abs(dc):
        step = (r1 + (1 if dr > 0 else -1), c1)
    elif abs(dc) > 0:
        step = (r1, c1 + (1 if dc > 0 else -1))
    else:
        step = from_node
    return step

def is_valid(node, maze):
    rows, cols = len(maze), len(maze[0])
    r, c = node
    return 0 <= r < rows and 0 <= c < cols and maze[r][c] == 0

def is_ancestor(tree, node, target):
    cur = node
    visited = set()
    while cur is not None:
        if cur == target:
            return True
        if cur in visited:
            break
        visited.add(cur)
        cur = tree.get(cur)
    return False

def extract_path(tree, goal):
    path = []
    cur = goal
    visited = set()

    while cur is not None:
        if cur in visited:
            return None   
        visited.add(cur)
        path.append(cur)
        cur = tree.get(cur)

    return path[::-1]

def find_goal_candidates(tree, goal, threshold=1):
    candidates = []
    for node in tree:
        if distance(node, goal) <= threshold:
            candidates.append(node)
    return candidates

def is_edge_valid(from_node, to_node, maze):
    r1, c1 = from_node
    r2, c2 = to_node
    if r1 == r2 and c1 == c2:
        return True
    
    dr = abs(r2 - r1)
    dc = abs(c2 - c1)
    sr = 1 if r2 > r1 else -1
    sc = 1 if c2 > c1 else -1
    
    r, c = r1, c1
    
    if dr > dc:
        err = dr / 2.0
        while r != r2:
            if not is_valid((r, c), maze):
                return False
            err -= dc
            if err < 0:
                c += sc
                err += dr
            r += sr
    else:
        err = dc / 2.0
        while c != c2:
            if not is_valid((r, c), maze):
                return False
            err -= dr
            if err < 0:
                r += sr
                err += dc
            c += sc
    return is_valid((r2, c2), maze)

# RRT* 主算法
def rrt_star(
    maze,
    start,
    goal,
    max_iter=5000,
    radius=2,
    goal_sample_rate=0.2
):
    tree = {start: None}
    cost = {start: 0}
    best_path = None
    best_path_length = float('inf')

    rows, cols = len(maze), len(maze[0])
    if not is_valid(start, maze) or not is_valid(goal, maze):
        print("起点或终点无效！")
        return []

    for i in range(max_iter):
        # 目标偏置
        if random.random() < goal_sample_rate:
            rand = goal
        else:
            rand = (random.randint(0, rows-1), random.randint(0, cols-1))

        if not is_valid(rand, maze):
            continue

        nearest = get_nearest(tree, rand)
        new_node = steer(nearest, rand)

        if not is_valid(new_node, maze):
            continue

        if new_node in tree:
            continue

        
        if not is_edge_valid(nearest, new_node, maze):
            continue
      
        neighbors = [n for n in tree if distance(n, new_node) <= radius]

        best_parent = nearest
        min_cost = cost[nearest] + distance(nearest, new_node)

        for n in neighbors:
            if is_edge_valid(n, new_node, maze):
                new_cost = cost[n] + distance(n, new_node)
                if new_cost < min_cost:
                    best_parent = n
                    min_cost = new_cost

        tree[new_node] = best_parent
        cost[new_node] = min_cost

        for n in neighbors:
            if n == best_parent:
                continue
            if is_edge_valid(new_node, n, maze):
                new_cost = cost[new_node] + distance(new_node, n)
                if new_cost < cost.get(n, float('inf')):
                    if not is_ancestor(tree, new_node, n):
                        tree[n] = new_node
                        cost[n] = new_cost

        if distance(new_node, goal) <= 1:
            if is_edge_valid(new_node, goal, maze):
                temp_tree = copy.copy(tree)
                temp_tree[goal] = new_node
                path = extract_path(temp_tree, goal)
                if path is not None:
                    path_length = len(path)
                    if path_length < best_path_length:
                        best_path = path
                        best_path_length = path_length
                        return best_path

    return best_path if best_path else []

async def show_path(level, player, path, block_id, base_x, base_y, base_z):
    if not path:
        print("没有路径可显示")
        return
    for i, (r, c) in enumerate(path):
        x = base_x + r
        z = base_z + c
        await level.set_block(x, base_y-1, z, block_id)
        await player.teleport(x, base_y + 1, z)
        await asyncio.sleep(0.3)

async def main():
    mc = PyModClient()
    await mc.connect()
    try:
        level = mc.overworld()
        players = await level.get_players()
        player = players[0]
        x, y, z = await player.get_pos()
        base_x = int(x)
        base_y = int(y)
        base_z = int(z)
        
        maze = create_maze()
        await draw_maze(level, maze, base_x, base_y, base_z)
        
        start = (0, 0)
        end = (9, 9)
        
        # 验证起点和终点是否有效
        if not is_valid(start, maze):
            print("错误：起点在墙内！")
            return
        if not is_valid(end, maze):
            print("错误：终点在墙内！")
            return
        
        path = rrt_star(maze, start, end)
        
        if path:
            print(f"找到路径，长度: {len(path)}")
            # 验证路径的每个点是否有效
            valid_path = True
            for point in path:
                if not is_valid(point, maze):
                    print(f"警告：路径点 {point} 在墙内！")
                    valid_path = False
            if valid_path:
                gold = "minecraft:gold_block"
                await show_path(level, player, path, gold, base_x, base_y, base_z)
            else:
                print("路径包含无效点")
        else:
            print("未找到路径")
            red_wool = "minecraft:red_wool"
            blue_wool = "minecraft:blue_wool"
            await level.set_block(base_x + start[0], base_y-1, base_z + start[1], red_wool)
            await level.set_block(base_x + end[0], base_y-1, base_z + end[1], blue_wool)  
    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())