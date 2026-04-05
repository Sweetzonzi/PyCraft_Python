import asyncio
from pycraft import PyModClient

async def build_house():
    """展示多方块的放置并建造房子"""
    client = PyModClient()
    await client.connect()
    
    try:
        level = client.overworld()
        
        # 获取玩家位置
        players = await level.get_players()
        player = players[0]
        px, py, pz = await player.get_pos()
        print(f"玩家位置: ({px:.1f}, {py:.1f}, {pz:.1f})")
        
        # 在玩家前方5格建造房子
        start_x = int(px + 5)
        start_y = int(py) - 1
        start_z = int(pz)
        
        # 房子范围：5x5地板，4格高
        # 清除区域：7x7平地（比房子大一点）
        clear_size = 7
        clear_x1 = start_x - 1
        clear_z1 = start_z - 3
        clear_x2 = start_x + 5
        clear_z2 = start_z + 3
        
        # 清除平地
        for x in range(clear_x1, clear_x2 + 1):
            for z in range(clear_z1, clear_z2 + 1):
                # 清除地面到屋顶高度的所有方块
                for y in range(start_y, start_y + 6):
                    await level.set_block(x, y, z, "minecraft:air")
        
        # 建造房子
        # 地板 (5x5)
        await level.set_blocks(start_x, start_y, start_z - 2, start_x + 4, start_y, start_z + 2, "minecraft:stone_bricks")
        
        # 前墙
        await level.set_blocks(start_x, start_y + 1, start_z - 2, start_x + 4, start_y + 3, start_z - 2, "minecraft:oak_planks")
        # 后墙
        await level.set_blocks(start_x, start_y + 1, start_z + 2, start_x + 4, start_y + 3, start_z + 2, "minecraft:oak_planks")
        # 左墙
        await level.set_blocks(start_x, start_y + 1, start_z - 2, start_x, start_y + 3, start_z + 2, "minecraft:oak_planks")
        # 右墙
        await level.set_blocks(start_x + 4, start_y + 1, start_z - 2, start_x + 4, start_y + 3, start_z + 2, "minecraft:oak_planks")
        
        # 屋顶
        await level.set_blocks(start_x, start_y + 4, start_z - 2, start_x + 4, start_y + 4, start_z + 2, "minecraft:glass")
        
        # 门洞（清除前墙中间）
        door_x = start_x + 2
        await level.set_block(door_x, start_y + 1, start_z - 2, "minecraft:air")
        await level.set_block(door_x, start_y + 2, start_z - 2, "minecraft:air")
        
    finally:
        await client.close()

asyncio.run(build_house())