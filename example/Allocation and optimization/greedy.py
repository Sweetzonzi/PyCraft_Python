from pycraft import PyModClient
import asyncio

"""自定义配置"""
# 背包总容量上限（可自由修改）
BACKPACK_CAPACITY = 50

# 物品定义：每个物品 = 名称 : {价值: int, 占用容量: int}
ITEMS = {
    "钻石":      {"value": 100, "weight": 9},   # 价值100，占5容量
    "黄金":      {"value": 50,  "weight": 6},   # 价值50，占3容量
    "铁锭":      {"value": 20,  "weight": 4},   # 价值20，占2容量
    "煤炭":      {"value": 5,   "weight": 2},   # 价值5，占1容量
    "圆石":      {"value": 1,   "weight": 1},   # 价值1，占1容量
}

# 游戏内方块映射（可视化用）
BLOCK_MAP = {
    "钻石": "minecraft:diamond_block",
    "黄金": "minecraft:gold_block",
    "铁锭": "minecraft:iron_block",
    "煤炭": "minecraft:coal_block",
    "圆石": "minecraft:cobblestone"
}

"""贪婪算法"""
def greedy_backpack():
    """
    分数背包贪婪算法：
    按单位容量价值(价值/容量) 降序排序，优先选择高性价比物品
    """
    # 计算每个物品的 单位容量价值
    item_list = []
    for name, info in ITEMS.items():
        value_per_weight = info["value"] / info["weight"]
        item_list.append((-value_per_weight, name, info))  # 负号=降序排序

    item_list.sort()
    remaining_capacity = BACKPACK_CAPACITY  # 剩余容量
    total_value = 0                         # 总价值
    best_items = {}                         # 最终选择的物品

    print(f"\n背包总容量：{BACKPACK_CAPACITY}")
    print("物品性价比排序（从高到低）：")

    # 贪婪选择：优先拿性价比最高的
    for _, name, info in item_list:
        if remaining_capacity <= 0:
            break

        weight = info["weight"]
        value = info["value"]
        # 最多能拿多少个当前物品
        max_count = remaining_capacity // weight

        if max_count > 0:
            best_items[name] = max_count
            total_value += max_count * value
            remaining_capacity -= max_count * weight
            print(f"选择 {name} × {max_count} | 占用容量：{max_count*weight} | 新增价值：{max_count*value}")

    return best_items, total_value, BACKPACK_CAPACITY - remaining_capacity

"""游戏内可视化"""
async def show_result(level, player, x, y, z, result):
    """用方块展示最优物品组合"""
    # 清空区域
    await level.set_blocks(x, y, z, x + 10, y + 6, z + 2, "minecraft:air")

    # 摆放对应方块
    offset = 0
    for item_name, count in result.items():
        block = BLOCK_MAP.get(item_name, "minecraft:stone")
        for i in range(count):
            await level.set_block(x + offset, y, z + i, block)
        offset += 2

    # 传送玩家
    await player.teleport(x + 5, y + 2, z + 1)

"""主函数"""
async def main():
    mc = PyModClient()
    await mc.connect()

    try:
        level = mc.overworld()
        players = await level.get_players()
        player = players[0]
        pos = await player.get_pos()
        x, y, z = int(pos[0]), int(pos[1]), int(pos[2])

        # 执行贪婪算法
        best_items, total_val, used_cap = greedy_backpack()

        # 输出最终结果
        print("\n" + "="*60)
        print("贪婪算法 - 背包价值最大化结果")
        print(f"最优组合：{best_items}")
        print(f"总价值：{total_val}")
        print(f"已用容量：{used_cap}/{BACKPACK_CAPACITY}")
        print("="*60)

        # 游戏内展示
        await show_result(level, player, x, y, z, best_items)

    finally:
        await mc.close()

if __name__ == "__main__":
    asyncio.run(main())