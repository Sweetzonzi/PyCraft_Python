import asyncio
from pycraft.client import PyModClient
from pycraft.api.uav import UavEntity

async def main():
    mc = PyModClient("localhost", 8086)
    await mc.connect()
    print("Connected to server")
    try:
        overworld = mc.overworld()
        """
        players = await overworld.get_players()
        player = players[0]
        x,y,z = await player.get_pos()
        """
        # 获取 UAV 列表
        uavs = await overworld.get_uav_list()
        if len(uavs) == 0:
            print("没有找到 UAV")
            return
        print("UAV列表:", uavs)
        uav = UavEntity(overworld, uavs[0]["agent_id"])
        state = await uav.get_state()
        print("当前状态:", state)

        # 先悬停在当前高度
        await uav.set_target(state["x"], state["y"], state["z"])
        await asyncio.sleep(2)

        # 方形巡航路径
        path = [
            (state["x"] + 10, state["y"] + 10, state["z"]),
            (state["x"] + 10, state["y"] + 10, state["z"] + 10),
            (state["x"], state["y"] + 10, state["z"] + 10),
            (state["x"], state["y"] + 10, state["z"]),
        ]

        print("开始巡航")

        for point in path:
            print("前往:", point)
            await uav.set_target(*point)
            await asyncio.sleep(5)
            # 实时打印状态
            state = await uav.get_state()
            print("当前状态:", state)
        print("巡航结束，返回原点")
    
    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())