# kmeans_uav.py
import asyncio
import random
import json
from pycraft import PyModClient
from env import load_env

K = 3
MAX_ITER = 20

def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def kmeans(points, k=3):
    # 随机初始化中心
    centers = random.sample(points, k)
    for _ in range(MAX_ITER):
        clusters = [[] for _ in range(k)]
        # 分配
        for p in points:
            dists = [dist(p, c) for c in centers]
            idx = dists.index(min(dists))
            clusters[idx].append(p)
        # 更新中心
        new_centers = []
        for cluster in clusters:
            if len(cluster) == 0:
                new_centers.append(random.choice(points))
                continue
            avg_x = sum(p[0] for p in cluster) / len(cluster)
            avg_z = sum(p[1] for p in cluster) / len(cluster)
            new_centers.append((int(avg_x), int(avg_z)))
        # 收敛判断
        if new_centers == centers:
            break
        centers = new_centers
    return centers, clusters

# 建无人机站
async def build_station(level, x, y, z):
    size = 6
    height = 3
    await level.set_blocks(x, y, z, x+size, y, z+size, "minecraft:stone")
    await level.set_blocks(x, y+1, z, x+size, y+height, z+size, "minecraft:air")
    await level.set_blocks(x, y+1, z, x+size, y+height, z, "minecraft:iron_block")
    await level.set_blocks(x, y+1, z+size, x+size, y+height, z+size, "minecraft:iron_block")
    await level.set_blocks(x, y+1, z, x, y+height, z+size, "minecraft:iron_block")
    await level.set_blocks(x+size, y+1, z, x+size, y+height, z+size, "minecraft:iron_block")

async def main():
    client = PyModClient()
    await client.connect()
    level = client.overworld()
    players = await level.get_players()
    player = players[0]
    x, y, z = await player.get_pos()

    data = load_env() # 读取房屋分布数据
    houses = data["houses"]
    # 只取 (x, z)
    points = [(h[0], h[2]) for h in houses]
    # K-means
    centers, clusters = kmeans(points, K)
    print("K-means中心:", centers)

    for i, (cx, cz) in enumerate(centers):
        print(f"生成第{i+1}个站点:", cx, cz)
        await build_station(level, cx, y, cz)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())