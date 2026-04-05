import asyncio
import math
from pycraft import PyModClient

async def walk_in_circle():
    """让玩家走圆形路径"""
    client = PyModClient()
    await client.connect()
    
    try:
        level = client.overworld()
        players = await level.get_players()
        player = players[0]
        await player.set_perspective(1)
        
        # 获取玩家当前位置
        px, py, pz = await player.get_pos()
        print(f"玩家 {player.name} 当前位置: ({px:.1f}, {py:.1f}, {pz:.1f})")
        
        # 以玩家位置为圆心，创建半径15格的圆形平地
        center_x, center_z = int(px), int(pz)
        ground_y = int(py) - 1  # 玩家脚下1格作为地面
        radius = 15
        blocks_placed = 0
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                # 计算到圆心的距离，只填充圆形区域
                dist = math.sqrt(dx * dx + dz * dz)
                if dist <= radius:
                    x = center_x + dx
                    z = center_z + dz
                    # 检查当前位置是否是空气，如果是则填充
                    current_block = await level.get_block(x, ground_y, z)
                    if current_block in ["minecraft:air", "minecraft:cave_air", "minecraft:void_air"]:
                        await level.set_block(x, ground_y, z, "minecraft:grass_block")
                        blocks_placed += 1              
        # 在平地上标记圆心
        await level.set_block(center_x, ground_y + 1, center_z, "minecraft:gold_block")
        print("在圆心放置了金块标记")
        
        # 让玩家走圆形路径
        # 使用刚才创建的平地的圆心作为路径中心
        walk_radius = 10  # 行走半径小于平地半径，确保在平地上
        y = ground_y + 1  # 站在平地表面
        
        # 先将玩家传送到起点（圆形路径的起点）
        start_angle = 0
        start_x = center_x + walk_radius * math.cos(start_angle)
        start_z = center_z + walk_radius * math.sin(start_angle)
        await player.teleport(start_x, y, start_z)
        await asyncio.sleep(0.5)  # 等待传送完成
        
        # 生成圆形路径点（36个点，每10度一个点）
        points = []
        for i in range(37):  # 37个点完成一圈（包括起点）
            angle = math.radians(i * 10)
            x = center_x + walk_radius * math.cos(angle)
            z = center_z + walk_radius * math.sin(angle)
            points.append((x, y, z))

        # 让玩家沿着路径移动
        for i, (x, y, z) in enumerate(points):
            print(f"移动到点 {i+1}/37: ({x:.2f}, {y}, {z:.2f})")
            
            # 使用 move_to 让实体平滑移动到目标位置
            # speed=0.2 表示移动速度，可以根据需要调整
            await player.move_to(x, y, z, speed=0.2)
            
            # 如果移动太慢可以减少等待时间，或根据距离动态计算
            await asyncio.sleep(0.3)
        
        # 移动完成后在玩家位置生成一些庆祝粒子
        await level.spawn_particle(center_x, y + 2, center_z, particle="happy_villager", count=20)
        await level.spawn_particle(center_x, y + 1, center_z, particle="note", count=10)
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(walk_in_circle())