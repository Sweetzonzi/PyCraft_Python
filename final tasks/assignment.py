import asyncio
import random
from pycraft import PyModClient
from env import load_env
import json

SAVE_ASSIGN_PATH = "./final tasks/assignment.json"

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# 贪心分配
def assignment(uavs, orders):
    """
    uavs: [(x,z), ...]
    orders: [(x,z), ...]
    """
    remaining_uavs = set(range(len(uavs)))
    remaining_orders = set(range(len(orders)))
    assignment = {}
    while remaining_uavs and remaining_orders:
        best_pair = None
        best_cost = float("inf")
        for uid in remaining_uavs:
            for oid in remaining_orders:
                cost = manhattan(uavs[uid], orders[oid])
                if cost < best_cost:
                    best_cost = cost
                    best_pair = (uid, oid)
        uid, oid = best_pair
        assignment[oid] = uid
        remaining_uavs.remove(uid)
        remaining_orders.remove(oid)
    return assignment


async def main():
    client = PyModClient()
    await client.connect()
    level = client.overworld()

    # 读取地图
    data = load_env()
    houses = data["houses"]
    house_map = [(h[0], h[2]) for h in houses]

    # 随机选3个订单
    orders = random.sample(house_map, 3)
    print("订单:", orders)

    # 获取 UAV
    resp = await client.request("get_uav_list", {})
    uavs_raw = resp["data"]["uavs"]
    uavs = [{"id": u["agent_id"], "x": u["x"], "z": u["z"]} for u in uavs_raw]
    uav_pos = [(u["x"], u["z"]) for u in uavs]
    print("UAV:", uavs)

    result = assignment(uav_pos, orders)

    for oid, uid in result.items():
        print(f"订单{oid} -> UAV{uid}")

    tasks = []
    for oid, uid in result.items():
        ox, oz = orders[oid]
        ux = int(uavs[uid]["x"])
        uz = int(uavs[uid]["z"])
        task = {
            "uav_id": uavs[uid]["id"],
            "order_id": oid,
            "start": [ux, uz],
            "goal": [int(ox), int(oz)]
        }
        tasks.append(task)

    # 保存分配结果
    with open(SAVE_ASSIGN_PATH, "w") as f:
        json.dump({"tasks": tasks}, f, indent=2)
    print("任务已保存:", SAVE_ASSIGN_PATH)
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())