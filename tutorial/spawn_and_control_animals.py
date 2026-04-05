import asyncio
import math
from pycraft import PyModClient

async def spawn_and_control_animal():
    """生成动物实体并控制移动"""
    client = PyModClient()
    await client.connect()
    
    try:
        level = client.overworld()
        players = await level.get_players()
        player = players[0]
        await player.set_perspective(1)
        px, py, pz = await player.get_pos()
        print(f"玩家位置: ({px:.1f}, {py:.1f}, {pz:.1f})")
        
        # 生成猪实体
        animal = await level.spawn_entity("pig", px + 3, py, pz, is_agent=True)
        animal.name = "pig"
        animal.type = "pig"
        print(f"已生成pig (ID: {animal.entity_id})")
        
        # 绕玩家走圈
        radius = 5
        points = []
        for i in range(37):
            angle = math.radians(i * 10)
            x = px + radius * math.cos(angle)
            z = pz + radius * math.sin(angle)
            points.append((x, py, z))
    
        print("开始绕圈...")
        for i, (x, y, z) in enumerate(points):
            await animal.move_to(x, y, z, speed=0.2)
            await asyncio.sleep(0.3)
        print("绕圈完成！")
        
        # 显示信息
        pos = await animal.get_pos()
        print(f"最终位置: {pos}")
        
        # 3秒后清除实体
        await asyncio.sleep(3)
        await animal.remove()
        print("已清除")
        
    finally:
        await client.close()

asyncio.run(spawn_and_control_animal())