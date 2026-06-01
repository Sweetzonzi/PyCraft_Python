import random
import math
import asyncio
from typing import List, Tuple
from pycraft import PyModClient

# 常量定义
FARMLAND_BLOCK = "minecraft:farmland"
WATER_BLOCK = "minecraft:water"
STONE_BLOCK = "minecraft:stone"
WOOD_BLOCK = "minecraft:oak_planks"
AIR_BLOCK = "minecraft:air"
GRASS_BLOCK = "minecraft:grass_block"

AIR_BLOCKS = {
    "minecraft:air",
    "air",
    "minecraft:cave_air",
    "minecraft:void_air",
    ""
}


def kmeans(points, k=3, max_iter=100):
    # 随机初始化中心
    centers = random.sample(points, k)

    for _ in range(max_iter):
        clusters = [[] for _ in range(k)]

        # 分配
        for i, p in enumerate(points):
            dists = [
                math.sqrt((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2)
                for c in centers
            ]
            idx = dists.index(min(dists))
            clusters[idx].append(i)  # 存索引

        # 更新中心
        new_centers = []
        for cluster in clusters:
            if len(cluster) == 0:
                new_centers.append(random.choice(points))
                continue

            avg_x = sum(points[i][0] for i in cluster) / len(cluster)
            avg_z = sum(points[i][1] for i in cluster) / len(cluster)
            new_centers.append((avg_x, avg_z))

        # 收敛判断
        if new_centers == centers:
            break

        centers = new_centers

    return centers, clusters


class Farm:
    x: int
    z: int
    y: int = 0

    def center(self):
        return (self.x + 1.5, self.z + 1.5)

    def water_block(self):
        return (self.x + 1, self.y, self.z + 1)

    def blocks(self):
        return [
            (self.x + dx, self.y, self.z + dz)
            for dx in range(3)
            for dz in range(3)
            if not (dx == 1 and dz == 1)
        ]

    def distance_to(self, point):
        cx, cz = self.center()
        px, pz = point
        return math.sqrt((cx - px) ** 2 + (cz - pz) ** 2)


class Hub:
    def __init__(self, x, z, y, height=3, assigned_farms=None):
        self.x = x
        self.z = z
        self.y = y
        self.height = height
        self.assigned_farms = assigned_farms or []

    def center(self):
        return (self.x + 0.5, self.z + 0.5)

    def platform_blocks(self):
        return [
            (self.x + dx, self.y, self.z + dz)
            for dx in range(-1, 2)
            for dz in range(-1, 2)
        ]


class AgriculturalSystem:
    def __init__(self, width=100, height=100, base_y=60):
        self.width = width
        self.height = height
        self.base_y = base_y

        self.farms = []
        self.hubs = []

    def generate_farms(self, min_count=50, max_count=70):
        farm_count = random.randint(min_count, max_count)
        farms = []
        occupied = set()

        while len(farms) < farm_count:
            x = random.randint(0, self.width - 3)
            z = random.randint(0, self.height - 3)

            overlap = any(
                (x + dx, z + dz) in occupied
                for dx in range(3)
                for dz in range(3)
            )

            if not overlap:
                farm = Farm()
                farm.x = x
                farm.z = z
                farm.y = self.base_y

                farms.append(farm)

                for dx in range(3):
                    for dz in range(3):
                        occupied.add((x + dx, z + dz))

        self.farms = farms
        return farms

    def optimize_hubs(self, k=3):
        if not self.farms:
            raise ValueError("请先生成农田")

        points = [farm.center() for farm in self.farms]

        centers, clusters = kmeans(points, k)

        hubs = []
        for i, center in enumerate(centers):
            hub_x = int(round(center[0] - 0.5))
            hub_z = int(round(center[1] - 0.5))

            hub_x = max(1, min(self.width - 2, hub_x))
            hub_z = max(1, min(self.height - 2, hub_z))

            assigned = [self.farms[idx] for idx in clusters[i]]

            hubs.append(Hub(hub_x, hub_z, self.base_y, assigned_farms=assigned))

        self.hubs = hubs
        return hubs

    def calculate_statistics(self):
        total = 0
        sizes = []

        for hub in self.hubs:
            sizes.append(len(hub.assigned_farms))
            for farm in hub.assigned_farms:
                total += farm.distance_to(hub.center())

        return {
            "farm_count": len(self.farms),
            "hub_count": len(self.hubs),
            "cluster_sizes": sizes,
            "total_distance": total
        }

    async def build(self, level, offset_x=0, offset_z=0, offset_y=0, clear_height=12):
        """
        在世界中建造农业系统。

        Args:
            level: PyCraft世界对象
            offset_x: 农业系统在世界坐标中的X偏移
            offset_z: 农业系统在世界坐标中的Z偏移
            offset_y: 高度偏移，默认0
            clear_height: 清理地面上方多少格的空间
        """
        base_y = self.base_y + offset_y

        print("正在铺设地面并清理上方空间...")
        print(
            f"农业系统区域: "
            f"X=[{offset_x}, {offset_x + self.width}], "
            f"Y={base_y}, "
            f"Z=[{offset_z}, {offset_z + self.height}]"
        )

        # 地面：先铺一层草方块，保证农田一定落在实体地面上
        await level.set_blocks(
            offset_x, base_y, offset_z,
            offset_x + self.width, base_y, offset_z + self.height,
            GRASS_BLOCK
        )

        # 清理地面上方空间，避免树叶、树干、石头等挡住农田
        await level.set_blocks(
            offset_x, base_y + 1, offset_z,
            offset_x + self.width, base_y + clear_height, offset_z + self.height,
            AIR_BLOCK
        )

        # 农田
        print("正在生成农田...")
        for farm in self.farms:
            for x, y, z in farm.blocks():
                await level.set_block(
                    x + offset_x,
                    y + offset_y,
                    z + offset_z,
                    FARMLAND_BLOCK
                )

            wx, wy, wz = farm.water_block()
            await level.set_block(
                wx + offset_x,
                wy + offset_y,
                wz + offset_z,
                WATER_BLOCK
            )

        # 枢纽
        print("正在生成枢纽平台...")
        for hub in self.hubs:
            for x, y, z in hub.platform_blocks():
                await level.set_block(
                    x + offset_x,
                    y + offset_y,
                    z + offset_z,
                    STONE_BLOCK
                )


async def find_ground_y_below_player(
    level,
    x: int,
    start_y: int,
    z: int,
    min_y: int = -64
) -> int:
    """
    从玩家当前位置向下扫描，寻找第一个非空气方块的Y坐标。
    """
    print(f"开始从玩家下方向下扫描地面: x={x}, start_y={start_y}, z={z}")

    for y in range(start_y, min_y - 1, -1):
        try:
            block_name = await level.get_block(x, y, z)

            if block_name not in AIR_BLOCKS:
                print(f"找到地面方块: {block_name}, 坐标=({x}, {y}, {z})")
                return y

        except Exception as e:
            print(f"获取方块失败: ({x}, {y}, {z}), 错误: {e}")
            break

    fallback_y = start_y - 1
    print(f"未能扫描到地面，退回估算高度: y={fallback_y}")
    return fallback_y


async def get_player_based_build_position(level, system_width: int, system_height: int):
    """
    获取玩家位置，并计算农业系统的建造位置。

    返回:
        base_y: 农田生成高度
        offset_x: 农业系统X方向世界偏移
        offset_z: 农业系统Z方向世界偏移
    """
    print("正在获取玩家位置...")

    try:
        players = await level.get_players()

        if not players:
            print("没有找到玩家，使用默认位置生成")
            return 60, 0, 0

        player = players[0]
        px, py, pz = await player.get_pos()

        player_x = int(round(px))
        player_z = int(round(pz))

        # 从玩家当前位置稍微往上开始扫描，防止站在半砖、作物、水面等特殊方块上时判断偏低
        start_y = int(py) + 2

        ground_y = await find_ground_y_below_player(
            level,
            player_x,
            start_y,
            player_z
        )

        # 让农业系统以玩家附近为中心展开
        offset_x = player_x - system_width // 2
        offset_z = player_z - system_height // 2

        print(f"玩家当前位置: x={px:.2f}, y={py:.2f}, z={pz:.2f}")
        print(f"检测到玩家下方地面高度: ground_y={ground_y}")
        print(f"农业系统世界偏移: offset_x={offset_x}, offset_z={offset_z}")

        return ground_y, offset_x, offset_z

    except Exception as e:
        print(f"获取玩家位置或扫描地面失败，使用默认位置生成: {e}")
        return 60, 0, 0

async def demo():
    client = PyModClient()
    await client.connect()
    level = client.overworld()

    try:
        # 先创建系统对象，用于确定宽高
        system = AgriculturalSystem(width=100, height=100)

        # 根据玩家位置和玩家下方真实地面高度，确定生成高度和偏移
        base_y, offset_x, offset_z = await get_player_based_build_position(
            level,
            system.width,
            system.height
        )

        # 把农田高度改成真实地面高度
        system.base_y = base_y

        # 生成农田与枢纽
        system.generate_farms()
        system.optimize_hubs()

        stats = system.calculate_statistics()
        print(stats)

        # 建造到玩家附近的真实地面上
        await system.build(
            level,
            offset_x=offset_x,
            offset_z=offset_z,
            offset_y=0
        )

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(demo())
