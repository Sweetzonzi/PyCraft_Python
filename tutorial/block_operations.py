import asyncio
from pycraft import PyModClient

async def block_operations():
    """展示方块的放置和查询操作"""
    client = PyModClient()
    await client.connect()
    
    try:
        level = client.overworld()
        
        """单个方块操作"""
        # 在 (0, 64, 0) 放置一个钻石块
        await level.set_block(0, 64, 0, "minecraft:diamond_block")
        print("在 (0, 64, 0) 放置了钻石块")
        
        # 查询该位置的方块类型
        block_type = await level.get_block(0, 64, 0)
        print(f"该位置的方块是: {block_type}")

    finally:
        await client.close()

asyncio.run(block_operations())