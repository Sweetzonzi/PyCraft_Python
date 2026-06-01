import asyncio
from pycraft.client import PyModClient


async def fly_to_point_with_drawing(uav, overworld, target, flown_path):
    """
    控制无人机飞向 target，并在飞行过程中实时绘制已经飞过的路径
    """
    print("前往:", target)

    await uav.set_target(*target)

    while True:
        state = await uav.get_state()

        cur_x = state["x"]
        cur_y = state["y"]
        cur_z = state["z"]

        current_pos = (cur_x, cur_y, cur_z)

        # 记录当前位置
        flown_path.append(current_pos)

        # 绘制已经飞过的轨迹
        await overworld.draw_path(flown_path, duration=5000)

        print("当前状态:", state)

        # 判断无人机是否接近目标点
        dx = cur_x - target[0]
        dy = cur_y - target[1]
        dz = cur_z - target[2]

        distance = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5

        if distance < 1.0:
            print("到达目标点:", target)
            break

        await asyncio.sleep(0.5)


async def main():
    mc = PyModClient("localhost", 8086)
    await mc.connect()
    print("Connected to server")

    try:
        overworld = mc.overworld()

        players = await overworld.get_players()
        player = players[0]
        x, y, z = await player.get_pos()

        # 生成无人机
        uav = await overworld.spawn_uav(x + 1, y, z)

        # 获取 UAV 列表
        uavs = await overworld.get_uav_list()
        if len(uavs) == 0:
            print("没有找到 UAV")
            return

        print("UAV列表:", uavs)

        # 获取当前状态
        state = await uav.get_state()
        print("当前状态:", state)

        start_x = state["x"]
        start_y = state["y"]
        start_z = state["z"]

        fly_y = start_y + 10

        # 用来保存已经飞过的轨迹
        flown_path = []

        # 先把起点加入轨迹
        flown_path.append((start_x, start_y, start_z))

        # 先悬停在当前位置
        await uav.set_target(start_x, start_y, start_z)
        await asyncio.sleep(2)

        # 起飞，同时画出起飞轨迹
        print("起飞")
        await fly_to_point_with_drawing(
            uav,
            overworld,
            (start_x, fly_y, start_z),
            flown_path
        )

        # 方形巡航路径
        path = [
            (start_x + 10, fly_y, start_z),
            (start_x + 10, fly_y, start_z + 10),
            (start_x, fly_y, start_z + 10),
            (start_x, fly_y, start_z),
        ]

        print("开始巡航")

        for point in path:
            await fly_to_point_with_drawing(
                uav,
                overworld,
                point,
                flown_path
            )

        print("巡航结束，返回原点")

        # 返回起飞前的位置，同时继续画路径
        await fly_to_point_with_drawing(
            uav,
            overworld,
            (start_x, start_y, start_z),
            flown_path
        )

        print("完成")

        await overworld.remove_uav(uav.agent_id)
        print("已删除")

    finally:
        await mc.close()


if __name__ == "__main__":
    asyncio.run(main())