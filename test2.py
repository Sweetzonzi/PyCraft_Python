import asyncio
from pycraft import PyModClient

async def main():
    mc = PyModClient()
    await mc.connect()
    try:
        overworld = mc.overworld()

        players = await overworld.get_players()
        print(players)
        player = players[0]

        time = await overworld.get_time()
        print(time)

        await player.set_perspective(1)
        pos1 = await player.get_pos()
        print(pos1)

        # 生成小猪
        pig = await overworld.spawn_entity(
            "minecraft:pig",
            -103.5, 67, 100.5
        )
        pig_id = pig.entity_id
        print(pig_id)

        # 持续追逐
        while True:
            # 获取小猪位置
            px, py, pz = await pig.get_pos()
            print(px)
            print(py)
            print(pz)

            # 获取玩家位置
            player_pos = await player.get_pos()
            print("Player:", player_pos, "Pig:", (px, py, pz))

            # 玩家移动到小猪
            await player.move_to(px, py, pz, speed=0.25)

            # 画轨迹
            await overworld.spawn_particle(px, py + 0.5, pz)

            await asyncio.sleep(0.05) 

    finally:
        await mc.close()

asyncio.run(main())