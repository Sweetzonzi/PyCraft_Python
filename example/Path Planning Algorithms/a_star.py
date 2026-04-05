from pycraft import PyModClient
import asyncio
import heapq

maze = [[0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
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
        # 这里只允许上下左右走
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.height and 0 <= ny < self.width and self.maze[nx][ny] == 0:
                neighbors.append((nx, ny))
        return neighbors

    def find_path(self, start, end):
        """
        核心寻路逻辑：使用 A* 算法查找从起点到终点的最短路径
        """
        # 确保输入是元组类型（tuple），因为元组是可哈希的，可以用作字典的键
        start = tuple(start)
        end = tuple(end)
        
        # open_set存储待探索的节点
        # 使用 heapq 实现优先级队列，元素格式为 (f_score, position)
        # 这样每次 pop 都能自动获取当前估计总代价最小的点
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        # came_from用于存储节点与其父节点的对应关系
        # 用于在到达终点后回溯出完整路径
        came_from = {}
        
        # g_score存储从起点到当前点的实际移动代价（步数）
        # 初始时起点的代价为 0
        g_score = {start: 0}
        
        # closed_set（关闭列表）：记录已经处理完成、找到最优路径的点
        # 防止重复计算，提高搜索效率
        closed_set = set()

        while open_set:
            # 从优先级队列中弹出当前 f_score 最小的点作为“当前节点”
            current_f, current = heapq.heappop(open_set)

            # 目标达成：如果当前点就是终点，开始构建路径
            if current == end:
                path = []
                # 通过 came_from 字典从终点往回跳，直到回到起点
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1] # 顺序反转

            # 如果当前点已经处理过，则跳过
            if current in closed_set:
                continue
            
            # 将当前点标记为已处理
            closed_set.add(current)

            # 遍历当前点的所有合法邻居（上下左右且非障碍物）
            for neighbor in self.get_neighbors(current):
                # tentative_g：从起点经过当前点到达邻居的临时代价
                # 因为是网格，每走一步代价增加 1
                tentative_g = g_score[current] + 1
                
                # 如果这个邻居还没走过，或者找到了一条到达该邻居更近的路径
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    # 记录/更新该邻居的父节点为当前点
                    came_from[neighbor] = current
                    # 更新起点到该邻居的实际代价 g
                    g_score[neighbor] = tentative_g
                    
                    # f = g(实际代价) + h(启发式预估代价)
                    # A* 算法通过 f 值来决定搜索的方向，向目标“贪婪”靠拢
                    f = tentative_g + self.heuristic(neighbor, end)
                    
                    # 将邻居及其 f 值加入队列，等待后续处理
                    heapq.heappush(open_set, (f, neighbor))

        # 如果队列空了还没找到终点，说明路径不通，返回空列表
        return []

async def show_path(level, player, path, block_id, base_x, base_y, base_z):
    if not path:
        print("警告：未找到有效路径！")
        return
    for r, c in path:
        x = base_x + r
        z = base_z + c

        await player.teleport(x + 0.5, base_y + 2, z + 0.5)
        await level.set_block(x, base_y - 1, z, block_id)

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
        await draw_maze(level, maze, base_x, base_y, base_z)
        start = [0, 0]
        end = [9, 9]
        a_star = AStar(maze)
        path = a_star.find_path(start, end)
        print(f"Path length: {len(path)}")
        gold = "minecraft:gold_block"
        await show_path(level, player, path, gold, base_x, base_y, base_z)
    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())