# env.py
import asyncio
import random
import json
from pycraft import PyModClient

SAVE_PATH = "./final tasks/village_map.json"
NUM_HOUSES = 50
WORLD_SIZE = 120   # 村庄范围
HOUSE_SIZE = 5
HOUSE_HEIGHT = 4
NUM_TREES = 50


def is_far_enough(pos, others, min_dist=8):
    for o in others:
        ox, oz = o[0], o[-1]
        if abs(pos[0] - ox) + abs(pos[1] - oz) < min_dist:
            return False
    return True

async def build_house(level, x, y, z):
    # 地基
    await level.set_blocks(x, y, z, x+HOUSE_SIZE, y, z+HOUSE_SIZE, "minecraft:stone")
    # 墙
    for h in range(1, HOUSE_HEIGHT):
        await level.set_blocks(x, y, z, x+HOUSE_SIZE, y+h, z, "minecraft:oak_planks")
        await level.set_blocks(x, y, z+HOUSE_SIZE, x+HOUSE_SIZE, y+h, z+HOUSE_SIZE, "minecraft:oak_planks")
        await level.set_blocks(x, y, z, x, y+h, z+HOUSE_SIZE, "minecraft:oak_planks")
        await level.set_blocks(x+HOUSE_SIZE, y, z, x+HOUSE_SIZE, y+h, z+HOUSE_SIZE, "minecraft:oak_planks")
    # 屋顶
    await level.set_blocks(x, y+HOUSE_HEIGHT, z, x+HOUSE_SIZE, y+HOUSE_HEIGHT, z+HOUSE_SIZE, "minecraft:oak_planks")
    # 门
    await level.set_block(x+2, y+1, z, "minecraft:air")
    await level.set_block(x+2, y+2, z, "minecraft:air")

async def build_tree(level, x, y, z):
    height = random.randint(3, 5)
    # 树干
    await level.set_blocks(x, y, z, x, y+height, z, "minecraft:mangrove_wood")
    # 树叶
    await level.set_blocks(x-1, y+height, z-1, x+1, y+height+1, z+1, "minecraft:dark_oak_leaves")

async def generate_env():
    client = PyModClient()
    await client.connect()
    level = client.overworld()
    players = await level.get_players()
    player = players[0]
    x, base_y, z = await player.get_pos()
    await level.set_blocks(x-120,base_y,z-120,x+120,base_y+20,z+120,"minecraft:air")
    houses = []
    obstacles = []

    while len(houses) < NUM_HOUSES:
        x = random.randint(-WORLD_SIZE, WORLD_SIZE)
        z = random.randint(-WORLD_SIZE, WORLD_SIZE)
        if is_far_enough((x, z), houses):
            await build_house(level, x, base_y, z)
            houses.append((x + HOUSE_SIZE//2, base_y, z + HOUSE_SIZE//2))

    while len(obstacles) < NUM_TREES:
        x = random.randint(-WORLD_SIZE, WORLD_SIZE)
        z = random.randint(-WORLD_SIZE, WORLD_SIZE)
        if is_far_enough((x, z), houses, 5):
            await build_tree(level, x, base_y, z)
            obstacles.append((x, base_y, z))

    # 保存地图数据
    data = {
        "houses": houses,
        "obstacles": obstacles
    }
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print("地图数据已保存:", SAVE_PATH)

    await client.close()

# 读取地图
def load_env():
    with open(SAVE_PATH, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    asyncio.run(generate_env())