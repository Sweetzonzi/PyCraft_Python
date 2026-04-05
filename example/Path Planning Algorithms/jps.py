import asyncio
import math
from pycraft import PyModClient

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

g_dir = [[1, 0], [0, 1], [0, -1], [-1, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]]
class Node:
    def __init__(self, parent, pos, g, h):
        self.parent = parent
        self.pos = pos
        self.g = g
        self.h = h
        self.f = g + h
    def get_direction(self):
        if not self.parent:
            return [0, 0]
        dx = self.pos[0] - self.parent.pos[0]
        dy = self.pos[1] - self.parent.pos[1]
        return [
            (dx // abs(dx)) if dx != 0 else 0,
            (dy // abs(dy)) if dy != 0 else 0
        ]
    
class JPS:
    def __init__(self, maze):
        self.s_pos = None
        self.e_pos = None
        self.width = len(maze[0])
        self.height = len(maze)
        self.open = []
        self.close = []
        self.path = []

    def prune_neighbours(self, c):
        """邻居修剪"""
        nbs = []
         # 不是起始点
        if c.parent:
            # 进入的方向
            dir = c.get_direction()
            if self.is_pass(c.pos[0] + dir[0], c.pos[1] + dir[1]):
                nbs.append([c.pos[0] + dir[0], c.pos[1] + dir[1]])
            # 对角线行走; eg:右下(1, 1)
            if dir[0] != 0 and dir[1] != 0:
                # 下（0， 1）
                if self.is_pass(c.pos[0], c.pos[1] + dir[1]):
                    nbs.append([c.pos[0], c.pos[1] + dir[1]])
                # 右（1， 0）
                if self.is_pass(c.pos[0]+dir[0], c.pos[1]):
                    nbs.append([c.pos[0]+dir[0], c.pos[1]])
                # 为防止穿墙情况的出现，做出如下改进：
                if self.is_pass(c.pos[0] + dir[0], c.pos[1]) or self.is_pass(c.pos[0], c.pos[1] + dir[1]):
                    if self.is_pass(c.pos[0] + dir[0], c.pos[1] + dir[1]):
                        nbs.append([c.pos[0] + dir[0], c.pos[1] + dir[1]])
                 
            else:  # 直行
                # 垂直走
                if dir[0] == 0:
                     # 右不能走
                    if not self.is_pass(c.pos[0]+1, c.pos[1]):
                        # 右下
                        nbs.append([c.pos[0]+1, c.pos[1]+dir[1]])
                     # 左不能走
                    if not self.is_pass(c.pos[0]-1, c.pos[1]):
                        # 左下
                        nbs.append([c.pos[0]-1, c.pos[1]+dir[1]])

                else:  # 水平走，向右走为例                     
                     # 下不能走
                    if not self.is_pass(c.pos[0], c.pos[1]+1):
                         # 右下
                         nbs.append([c.pos[0]+dir[0], c.pos[1]+1])
                     # 上不能走
                    if not self.is_pass(c.pos[0], c.pos[1]-1):
                         # 右上
                         nbs.append([c.pos[0]+dir[0], c.pos[1]-1])

        else:
            for d in g_dir:
                if self.is_pass(c.pos[0] + d[0], c.pos[1] + d[1]):
                    nbs.append([c.pos[0] + d[0], c.pos[1] + d[1]])
        return nbs
    # ↑ ↓ ← → ↖ ↙ ↗ ↘
    def jump_node(self, now, pre):  
        """寻找跳点"""
        dir = [
            int((now[0] - pre[0]) // abs(now[0] - pre[0])) if now[0] != pre[0] else 0,
            int((now[1] - pre[1]) // abs(now[1] - pre[1])) if now[1] != pre[1] else 0
        ]
        if now == self.e_pos:
            return now

        if self.is_pass(now[0], now[1]) is False:
            return None
        if dir[0] != 0 and dir[1] != 0:
            # 如果对角线路径被侧面的墙堵住了缝隙，直接停止此方向搜索
            if not self.is_pass(now[0] - dir[0], now[1]) and not self.is_pass(now[0], now[1] - dir[1]):
                return None
        else:
            # 水平方向
            if dir[0] != 0:
                # 右下能走且下不能走， 或右上能走且上不能走
                '''
                * 1 0       0 0 0
                0 → 0       0 0 0
                * 1 0       0 0 0
                
                '''
                if (self.is_pass(now[0] + dir[0], now[1] + 1) and not self.is_pass(now[0], now[1]+1)) or (self.is_pass(now[0] + dir[0], now[1] - 1) and not self.is_pass(now[0], now[1]-1)):
                    return now
            else: # 垂直方向
                # 右下能走且右不能走，或坐下能走且左不能走
                '''
                0 0 0
                1 ↓ 1
                0 0 0
                                
                '''
                if (self.is_pass(now[0] + 1, now[1] + dir[1]) and not self.is_pass(now[0]+1, now[1])) or (self.is_pass(now[0] - 1, now[1] + dir[1]) and not self.is_pass(now[0]-1, now[1])):
                    return now

        if dir[0] != 0 and dir[1] != 0:
            t1 = self.jump_node([now[0]+dir[0], now[1]], now)
            t2 = self.jump_node([now[0], now[1] + dir[1]], now)
            if t1 or t2:
                return now
        if self.is_pass(now[0] + dir[0], now[1]) or self.is_pass(now[0], now[1] + dir[1]):
            t = self.jump_node([now[0] + dir[0], now[1] + dir[1]], now)
            if t:
                return t

        return None

    def extend_round(self, c):
        """
        扩展当前节点：寻找所有潜在的跳点并更新开放列表
        """
        # 根据当前移动的方向，对邻居进行修剪
        nbs = self.prune_neighbours(c)
        
        for n in nbs:
            # 从邻居节点 n 开始，沿着当前方向 [c.pos -> n] 进行递归跳跃
            # jp 会返回找到的跳点坐标，如果该方向死路一条则返回 None
            jp = self.jump_node(n, [c.pos[0], c.pos[1]])
            
            if jp:
                # 如果该跳点已经在关闭列表则跳过
                if self.node_in_close(jp):
                    continue
                
                # 计算从当前点 c 到跳点 jp 的实际移动代价 g
                g = self.get_g(jp, c.pos)
                # 计算从跳点 jp 到终点的估算代价 h（启发式）
                h = self.get_h(jp, self.e_pos)
                
                # 创建一个新的节点对象，父节点指向当前点 c
                # 注意：g 值是累加的：c.g（起点到c的距离） + g（c到跳点的距离）
                node = Node(c, jp, c.g + g, h)
                
                # 检查这个跳点是否已经存在于开放列表（open_set）中
                i = self.node_in_open(node)
                
                if i != -1:
                    # 若跳点已经在开放列表中
                    # 比较当前路径的 g 值是否比之前记录的更短
                    if self.open[i].g > node.g:
                        # 发现了一条更短的路径到达该跳点：
                        # 1. 更新父节点为当前节点 c
                        self.open[i].parent = c
                        # 2. 更新起点到该点的实际代价 g
                        self.open[i].g = node.g
                        # 3. 重新计算总估价 f
                        self.open[i].f = node.g + self.open[i].h
                    # 处理完毕，继续看下一个邻居
                    continue
                
                # 若这是一个全新的跳点，直接加入开放列表等待后续扩展
                self.open.append(node)


    def is_pass(self, x, y):
        x, y = int(x), int(y)
        if 0<= x < self.height and 0 <= y < self.width:
            return maze[x][y] == 0 or [x, y] == self.e_pos
        return False


    # 查找路径的入口函数
    def find_path(self, s_pos, e_pos):
        self.s_pos, self.e_pos = s_pos, e_pos
        # 构建开始节点
        p = Node(None, self.s_pos, 0, abs(self.s_pos[0]-self.e_pos[0]) + abs(self.s_pos[1]-self.e_pos[1]))
        self.open.append(p)
        while True:
            # 扩展F值最小的节点
            # 如果开放列表为空，则不存在路径，返回
            if not self.open:
                return "not find"
            # 获取F值最小的节点
            idx, p = self.get_min_f_node()
            # 找到路径，生成路径，返回
            if self.is_target(p):
                self.make_path(p)
                return
            self.extend_round(p)
            # 把此节点压入关闭列表，并从开放列表里删除
            self.close.append(p)
            del self.open[idx]

    def make_path(self, p):
        # 从结束点回溯到开始点，开始点的parent == None
        while p:
            if p.parent:
                dir = p.get_direction()
                n = p.pos
                while n != p.parent.pos:
                    self.path.append(n)
                    n = [n[0] - dir[0], n[1] - dir[1]]
            else:
                self.path.append(p.pos)
            p = p.parent
        self.path.reverse()
    def is_target(self, n):
        return n.pos == self.e_pos

    def get_min_f_node(self):
        best = None
        bv = -1
        bi = -1
        for idx, node in enumerate(self.open):
            # value = self.get_dist(i)  # 获取F值
            if bv == -1 or node.f < bv:  # 比以前的更好，即F值更小
                best = node
                bv = node.f
                bi = idx
        return bi, best
    # 计算g值；直走=1；斜走=1.4
    def get_g(self, pos1, pos2):
        if pos1[0] == pos2[0]:
            return abs(pos1[1] - pos2[1])
        elif pos1[1] == pos2[1]:
            return abs(pos1[0] - pos2[0])
        else:
            return abs(pos1[0] - pos2[0]) * 1.4
    # 计算h值
    def get_h(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def node_in_close(self, node):
        for i in self.close:
            if node == i.pos:
                return True
        return False

    def node_in_open(self, node):
        for i, n in enumerate(self.open):
            if node == n.pos:
                return i
        return -1

    def get_searched(self):
        l = []
        for i in self.open:
            l.append((i.pos[0], i.pos[1]))
        for i in self.close:
            l.append((i.pos[0], i.pos[1]))
        return l

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
        jps = JPS(maze)
        jps.find_path(start, end)
        path = jps.path
        print(f"Path length: {len(path)}")
        gold = "minecraft:gold_block"
        await show_path(level, player, path, gold, base_x, base_y, base_z)
    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())