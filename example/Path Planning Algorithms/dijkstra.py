import asyncio
import heapq
import math
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

def dijkstra(maze, start, end):
    # 获取迷宫的行列数
    rows, cols = len(maze), len(maze[0])
    
    # 优先队列（最小堆），存储 (当前距离, 节点坐标)
    # 初始：起点距离为0
    pq = [(0, start)]
    
    # 记录每个节点的最短距离
    # 初始：只有起点，距离为0
    dist = {start: 0}
    
    # 记录每个节点的父节点，用于最后重建路径
    # 初始：起点没有父节点
    parent = {start: None}
    
    # 记录已访问过的节点，避免重复处理
    visited = set()
    
    # 主循环：当优先队列不为空时继续
    while pq:
        # 取出距离最小的节点
        # heapq.heappop 自动按元组第一个元素（距离）排序
        cost, cur = heapq.heappop(pq)
        
        # 如果已经访问过，跳过（说明之前已经找到更短路径）
        if cur in visited:
            continue
        
        # 标记为已访问
        visited.add(cur)
        
        # 到达终点，重建并返回路径
        if cur == end:
            path = []
            # 从终点回溯到起点
            while cur:
                path.append(cur)      # 加入当前节点
                cur = parent[cur]      # 移动到父节点
            return path[::-1]          # 反转，得到从起点到终点的顺序
        
        # 遍历4个方向：上、下、左、右
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            # 计算邻居坐标
            nr, nc = cur[0]+dr, cur[1]+dc
            
            # 检查邻居是否合法，即是否在迷宫范围内，是否是墙（值为0表示可通行）
            if 0 <= nr < rows and 0 <= nc < cols and maze[nr][nc] == 0:
                
                # 计算到邻居的新距离（本迷宫每步代价为1）
                new_cost = cost + 1
                
                # 如果邻居未访问过，或找到更短路径
                if (nr,nc) not in dist or new_cost < dist[(nr,nc)]:
                    
                    # 更新邻居的最短距离
                    dist[(nr,nc)] = new_cost
                    
                    # 记录邻居的父节点（用于重建路径）
                    parent[(nr,nc)] = cur
                    
                    # 将邻居加入优先队列
                    heapq.heappush(pq, (new_cost, (nr,nc)))
    
    # 队列空且未找到终点，说明不可达，返回空列表
    return []

def direction_to_yaw(dx, dz):
    """
    计算前进方向
    """
    return math.degrees(math.atan2(-dx, dz))

async def show_path(level, player, path, block_id, base_x, base_y, base_z):
    """
    一边走一边自动转向
    """
    for i in range(1, len(path)):
        x0, z0 = path[i-1]
        x1, z1 = path[i]
        dx = x1 - x0
        dz = z1 - z0
        yaw = direction_to_yaw(dx, dz)
        # 先转向
        await player.set_rotation(yaw)
        # 再移动
        x = base_x + x1
        z = base_z + z1
        await level.set_block(x, base_y-1, z, block_id)
        await player.teleport(x, base_y, z)
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
        path = dijkstra(maze, start, end)
        gold = "minecraft:gold_block"
        await player.set_perspective(1)
        await show_path(level, player, path, gold, base_x, base_y, base_z)
    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())