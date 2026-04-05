import asyncio
from pycraft import PyModClient

async def main():
    mc = PyModClient()
    await mc.connect()
    try:
        overworld = mc.overworld()
        '''
        await overworld.set_block(0, 100, 0, "minecraft:diamond_block")
        block = await overworld.get_block(0,100,0)
        print(block)
        '''
        players = await overworld.get_players()
        print(players)
        player = players[0]
        p = await player.get_pos()
        print(p)

        # 生成小猪
        pig = await overworld.spawn_entity(
            "minecraft:pig",
            -7.5, 102, -47.5
        )
        await pig.remove()
        '''
        # await player.move_to(120, 80, 120, 0.3)
        await player.teleport(120, 80, 120)
        pos = await player.get_pos()
        print(pos)
        time = await overworld.get_time()
        print(time)
        await player.set_perspective(1)
        x,y,z = await player.get_pos() 
        print(x,y,z)
        await overworld.spawn_particle(x,y+5,z,count=50)
        '''
        
        
    finally:
        await mc.close()

asyncio.run(main())