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

    async def build(self, level, offset_x=0, offset_z=0, offset_y=0):
        base_y = self.base_y + offset_y

        # 地面
        await level.set_blocks(
            offset_x, base_y, offset_z,
            offset_x + self.width, base_y, offset_z + self.height,
            "minecraft:grass_block"
        )

        # 农田
        for farm in self.farms:
            for x, y, z in farm.blocks():
                await level.set_block(x+offset_x, y+offset_y, z+offset_z, FARMLAND_BLOCK)

            wx, wy, wz = farm.water_block()
            await level.set_block(wx+offset_x, wy+offset_y, wz+offset_z, WATER_BLOCK)

        # 枢纽
        for hub in self.hubs:
            for x, y, z in hub.platform_blocks():
                await level.set_block(x+offset_x, y+offset_y, z+offset_z, STONE_BLOCK)


async def demo():
    system = AgriculturalSystem()

    system.generate_farms()
    system.optimize_hubs()

    stats = system.calculate_statistics()
    print(stats)

    client = PyModClient()
    await client.connect()
    level = client.overworld()

    await system.build(level)

    await client.close()


if __name__ == "__main__":
    asyncio.run(demo())