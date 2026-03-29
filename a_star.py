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
        start = tuple(start)
        end = tuple(end)
        
        # 优先级队列存储: (f_score, position)
        open_set = []
        heapq.heappush(open_set, (0, start))
        
        came_from = {}
        g_score = {start: 0}
        
        # 记录已经真正处理过的点
        closed_set = set()

        while open_set:
            # 获取 f_score 最小的点
            current_f, current = heapq.heappop(open_set)

            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1] # 返回翻转后的路径

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