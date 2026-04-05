import asyncio
from pycraft import PyModClient

async def find_and_teleport_player():
    """查找主世界中的玩家，并将其传送到指定位置"""
    # 创建客户端实例（默认连接 localhost:8086）
    client = PyModClient()

    # 连接服务器
    await client.connect()
    
    try:
        # 获取主世界
        level = client.overworld()
        
        # 获取该维度中的所有玩家
        players = await level.get_players()
        
        if not players:
            print("没有找到玩家！")
            return
        
        # 显示所有玩家位置
        for player in players:
            pos = await player.get_pos()
            print(f"玩家 {player.name} (ID: {player.entity_id}) 位于: {pos}")
        
        # 传送第一个玩家到指定坐标 (x=100, y=64, z=100)
        target_player = players[0]
        await target_player.set_perspective(1) # 0表示切换为第一人称视角，1表示切换为第三人称背面视角，2表示切换为第三人称正面视角
        await target_player.teleport(100, 64, 100)
        print(f"已将 {target_player.name} 传送到 (100, 64, 100)")
        
        # 验证新位置
        new_pos = await target_player.get_pos()
        print(f"新位置: {new_pos}")
        
    finally:
        # 关闭连接
        await client.close()

asyncio.run(find_and_teleport_player())