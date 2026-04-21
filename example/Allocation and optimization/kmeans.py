import numpy as np
import random
import math
import asyncio
from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
from pycraft import PyModClient

# 常量定义
FARMLAND_BLOCK = "minecraft:farmland"
WATER_BLOCK = "minecraft:water"
STONE_BLOCK = "minecraft:stone"
WOOD_BLOCK = "minecraft:oak_planks"  # 木块类型，可根据需要修改
AIR_BLOCK = "minecraft:air"

# 羊毛颜色常量（用于迭代可视化）
WHITE_WOOL = "minecraft:white_wool"
ORANGE_WOOL = "minecraft:orange_wool"
MAGENTA_WOOL = "minecraft:magenta_wool"
LIGHT_BLUE_WOOL = "minecraft:light_blue_wool"
YELLOW_WOOL = "minecraft:yellow_wool"
LIME_WOOL = "minecraft:lime_wool"
PINK_WOOL = "minecraft:pink_wool"
GRAY_WOOL = "minecraft:gray_wool"


class Farm:
    """表示一个3×3农田（中间为水源，周围8块可种植）"""
    x: int  # 左上角x坐标
    z: int  # 左上角z坐标
    y: int = 0  # 农田高度，默认y=0（与地面同一层）

    def center(self) -> Tuple[float, float]:
        """返回农田中心点坐标 (x+1.5, z+1.5)"""
        return (self.x + 1.5, self.z + 1.5)

    def water_block(self) -> Tuple[int, int, int]:
        """返回中间水源方块的坐标"""
        return (self.x + 1, self.y, self.z + 1)

    def blocks(self) -> List[Tuple[int, int, int]]:
        """返回农田八个可种植方块的坐标列表（排除中间水源）"""
        return [
            (self.x + dx, self.y, self.z + dz)
            for dx in range(3)
            for dz in range(3)
            if not (dx == 1 and dz == 1)  # 跳过中间的水源方块
        ]

    def distance_to(self, point: Tuple[float, float]) -> float:
        """计算农田中心到某点的欧氏距离"""
        cx, cz = self.center
        px, pz = point
        return math.sqrt((cx - px) ** 2 + (cz - pz) ** 2)


class Hub:
    """表示一个3×3农业枢纽"""
    x: int  # 中心x坐标（实际建筑从x-1开始）
    z: int  # 中心z坐标（实际建筑从z-1开始）
    y: int = 0  # 地基高度，默认y=0
    height: int = 3  # 建筑高度
    assigned_farms: List[Farm] = None  # 分配给该枢纽的农田

    def __post_init__(self):
        if self.assigned_farms is None:
            self.assigned_farms = []

    def center(self) -> Tuple[float, float]:
        """返回枢纽中心点坐标"""
        return (self.x + 0.5, self.z + 0.5)

    def platform_blocks(self) -> List[Tuple[int, int, int]]:
        """返回3×3平台的所有方块坐标"""
        return [
            (self.x + dx, self.y, self.z + dz)
            for dx in range(-1, 2)
            for dz in range(-1, 2)
        ]

    def building_blocks(self) -> List[Tuple[int, int, int]]:
        """返回整个建筑的所有方块坐标（平台+柱子+屋顶）"""
        blocks = []
        # 平台（石头）
        blocks.extend(
            (self.x + dx, self.y, self.z + dz)
            for dx in range(-1, 2)
            for dz in range(-1, 2)
        )

        # 四角柱子（石头）
        corner_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        blocks.extend(
            (self.x + dx, self.y + dy, self.z + dz)
            for dy in range(1, self.height)
            for dx, dz in corner_offsets
        )

        # 屋顶（木块）
        blocks.extend(
            (self.x + dx, self.y + self.height, self.z + dz)
            for dx in range(-1, 2)
            for dz in range(-1, 2)
        )

        return blocks

    def distance_to(self, point: Tuple[float, float]) -> float:
        """计算枢纽中心到某点的欧氏距离"""
        cx, cz = self.center
        px, pz = point
        return math.sqrt((cx - px) ** 2 + (cz - pz) ** 2)

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """判断点是否在枢纽区域内（包括3×3区域）"""
        px, pz = point
        return (self.x - 1 <= px <= self.x + 2) and (self.z - 1 <= pz <= self.z + 2)




class AgriculturalSystem:
    """农业系统主控制器"""
    def __init__(self, width: int = 100, height: int = 100, base_y: int = 60):
        """
        初始化农业系统
        width: 区域宽度（x方向）
        height: 区域高度（z方向）
        base_y: 基础高度（y坐标）
        """
        self.width = width
        self.height = height
        self.base_y = base_y

        self.farms: List[Farm] = []
        self.hubs: List[Hub] = []

        # 随机数种子
        random.seed()

    def generate_farms(self, min_count: int = 50, max_count: int = 70,
                      max_attempts: int = 1000) -> List[Farm]:
        """
        生成随机不重叠的农田
        min_count: 最少农田数量
        max_count: 最多农田数量
        max_attempts: 最大尝试次数（避免无限循环）
        """
        farm_count = random.randint(min_count, max_count)
        farms = []

        # 用于快速检测重叠的集合
        occupied = set()

        attempts = 0
        while len(farms) < farm_count and attempts < max_attempts:
            # 随机选择左上角坐标，确保3×3农田完全在区域内
            x = random.randint(0, self.width - 3)
            z = random.randint(0, self.height - 3)

            # 检查是否与现有农田重叠（检查3×3区域）
            overlap = any(
                (x + dx, z + dz) in occupied
                for dx in range(3)
                for dz in range(3)
            )

            if not overlap:
                # 创建农田并标记占用（占用全部3×3区域，包括中间水源）
                farm = Farm(x, z, self.base_y)
                farms.append(farm)
                for dx in range(3):
                    for dz in range(3):
                        occupied.add((x + dx, z + dz))

            attempts += 1

        if len(farms) < min_count:
            print(f"警告：只生成了{len(farms)}个农田，低于最小值{min_count}")

        self.farms = farms
        return farms

    def _kmeans(self, k: int = 3, max_iter: int = 100, n_init: int = 10,
                return_history: bool = False) -> Tuple[List[Tuple[float, float]], List[List[int]], Optional[List[np.ndarray]]]:
        """
        K-means聚类算法
        返回：聚类中心列表，每个簇的农田索引列表，可选的迭代历史
        """
        # 提取农田中心点
        points = np.array([farm.center for farm in self.farms])

        best_centers = None
        best_labels = None
        best_inertia = float('inf')
        best_history = []  # 存储最佳初始化的迭代历史

        for init in range(n_init):
            # 随机初始化聚类中心
            centers = points[np.random.choice(len(points), k, replace=False)]
            history = []  # 本次初始化的迭代历史

            for iteration in range(max_iter):
                # 记录当前中心点（在更新前）
                if return_history:
                    history.append(centers.copy())

                # 分配步骤：计算每个点到最近中心的距离
                distances = np.sqrt(((points[:, np.newaxis, :] - centers[np.newaxis, :, :]) ** 2).sum(axis=2))
                labels = np.argmin(distances, axis=1)

                # 更新步骤：重新计算中心
                new_centers = np.array([
                    points[labels == i].mean(axis=0) if np.any(labels == i) else centers[i]
                    for i in range(k)
                ])

                # 检查收敛
                if np.allclose(centers, new_centers, rtol=1e-4):
                    centers = new_centers
                    if return_history:
                        history.append(centers.copy())  # 记录最终中心点
                    break

                centers = new_centers

            # 如果循环结束但未记录最终中心点（当达到max_iter时）
            if return_history and len(history) == max_iter:
                history.append(centers.copy())

            # 计算损失（inertia）
            inertia = np.sum((points - centers[labels]) ** 2)

            if inertia < best_inertia:
                best_inertia = inertia
                best_centers = centers
                best_labels = labels
                if return_history:
                    best_history = history

        # 将标签转换为农田索引列表
        clusters = [[] for _ in range(k)]
        for idx, label in enumerate(best_labels):
            clusters[label].append(idx)

        if return_history:
            return best_centers, clusters, best_history
        else:
            return best_centers, clusters, None

    def optimize_hubs(self, k: int = 3, max_iter: int = 100, n_init: int = 10,
                      return_history: bool = False) -> Union[List[Hub], Tuple[List[Hub], List[np.ndarray]]]:
        """
        优化枢纽位置（K-means聚类）
        k: 枢纽数量
        max_iter: 最大迭代次数
        n_init: 随机初始化次数
        return_history: 是否返回迭代历史
        返回：枢纽列表，如果return_history=True则返回（枢纽列表，历史记录）
        """
        if not self.farms:
            raise ValueError("请先生成农田")

        centers, clusters, history = self._kmeans(k, max_iter, n_init, return_history)

        # 创建Hub对象
        hubs = []
        for i, center in enumerate(centers):
            # 将浮点中心坐标转换为整数网格坐标
            hub_x = int(round(center[0] - 0.5))  # 调整为中心坐标
            hub_z = int(round(center[1] - 0.5))

            # 确保枢纽在区域内且不与其他枢纽重叠
            hub_x = max(1, min(self.width - 2, hub_x))
            hub_z = max(1, min(self.height - 2, hub_z))

            # 获取分配给该枢纽的农田
            assigned_farms = [self.farms[idx] for idx in clusters[i]]

            hub = Hub(hub_x, hub_z, self.base_y, height=3, assigned_farms=assigned_farms)
            hubs.append(hub)

        self.hubs = hubs

        if return_history:
            return hubs, history
        else:
            return hubs


    def calculate_statistics(self) -> dict:
        """计算系统统计信息"""
        stats = {
            'farm_count': len(self.farms),
            'hub_count': len(self.hubs),
            'total_farm_hub_distance': 0,
            'hub_locations': [],
            'cluster_sizes': []
        }

        # 农田到枢纽的总距离
        total_hub_distance = 0
        for hub in self.hubs:
            stats['hub_locations'].append((hub.x, hub.z))
            stats['cluster_sizes'].append(len(hub.assigned_farms))
            for farm in hub.assigned_farms:
                total_hub_distance += farm.distance_to(hub.center)

        stats['total_farm_hub_distance'] = total_hub_distance


        return stats



    async def _build_iteration_hub(self, level, hub_x: int, hub_z: int,
                                 roof_block: str,
                                 offset_x: int = 0, offset_z: int = 0, offset_y: int = 0):
        """
        构建单个迭代枢纽（完整建筑结构，屋顶使用指定颜色的羊毛）
        返回：构建的方块位置列表，用于后续清除
        """
        hub_y = self.base_y + offset_y
        blocks = []

        # 平台（石头）- 3×3
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                x = hub_x + dx + offset_x
                y = hub_y
                z = hub_z + dz + offset_z
                await level.set_block(x, y, z, STONE_BLOCK)
                blocks.append((x, y, z))

        # 四角柱子（石头）- 高度固定为3
        for dy in range(1, 3):
            for dx, dz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                x = hub_x + dx + offset_x
                y = hub_y + dy
                z = hub_z + dz + offset_z
                await level.set_block(x, y, z, STONE_BLOCK)
                blocks.append((x, y, z))

        # 屋顶（使用指定颜色的羊毛）- 3×3
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                x = hub_x + dx + offset_x
                y = hub_y + 3
                z = hub_z + dz + offset_z
                await level.set_block(x, y, z, roof_block)
                blocks.append((x, y, z))

        return blocks

    async def build_iterations_sequential(self, level, history: List[np.ndarray],
                                        max_iterations: int = 3,
                                        delay_seconds: float = 2.0,
                                        offset_x: int = 0, offset_z: int = 0, offset_y: int = 0):
        """
        按顺序构建K-means迭代过程可视化
        history: 迭代历史记录
        max_iterations: 最多展示的迭代次数
        delay_seconds: 每次迭代之间的延迟时间（秒）
        """
        if not history:
            print("没有迭代历史记录")
            return

        # 限制显示的迭代次数
        display_history = history[:max_iterations]

        # 颜色序列（白色->橙色->洋红色->浅蓝色...）
        wool_colors = [
            WHITE_WOOL, ORANGE_WOOL, MAGENTA_WOOL,
            LIGHT_BLUE_WOOL, YELLOW_WOOL, LIME_WOOL,
            PINK_WOOL, GRAY_WOOL
        ]

        # 存储已构建的枢纽方块位置，用于清除
        previous_iteration_blocks = []

        for iter_num, centers in enumerate(display_history):
            color = wool_colors[iter_num % len(wool_colors)]

            # 清除前一次迭代的枢纽（除第一次外）
            if previous_iteration_blocks:
                print(f"清除第 {iter_num} 次迭代的枢纽...")
                for x, y, z in previous_iteration_blocks:
                    await level.set_block(x, y, z, AIR_BLOCK)
                previous_iteration_blocks.clear()

            print(f"构建第 {iter_num + 1} 次迭代枢纽（颜色: {color}）...")

            # 构建本次迭代的枢纽
            iteration_blocks = []
            for i, center in enumerate(centers):
                # 将浮点中心坐标转换为整数网格坐标
                hub_x = int(round(center[0] - 0.5))
                hub_z = int(round(center[1] - 0.5))

                # 确保枢纽在区域内
                hub_x = max(1, min(self.width - 2, hub_x))
                hub_z = max(1, min(self.height - 2, hub_z))

                # 构建单个迭代枢纽（完整建筑结构，屋顶使用指定颜色的羊毛）
                blocks = await self._build_iteration_hub(
                    level, hub_x, hub_z, color,
                    offset_x, offset_z, offset_y
                )
                iteration_blocks.extend(blocks)

            previous_iteration_blocks = iteration_blocks.copy()

            # 如果不是最后一次迭代，添加延迟
            if iter_num < len(display_history) - 1:
                print(f"等待 {delay_seconds} 秒...")
                await asyncio.sleep(delay_seconds)

        print(f"迭代可视化完成！共展示了 {len(display_history)} 次迭代。")

    async def build(self, level, clear_area: bool = True,
                   offset_x: int = 0, offset_z: int = 0, offset_y: int = 0):
        """
        在Minecraft中构建农业系统
        level: PyCraft Level对象
        clear_area: 是否先清理区域
        offset_x: X轴偏移（将整个系统平移）
        offset_z: Z轴偏移
        offset_y: Y轴偏移（相对于base_y）
        """
        base_y = self.base_y + offset_y

        if clear_area:
            # 清理区域（空气方块）
            await level.set_blocks(
                offset_x, base_y, offset_z,
                offset_x + self.width - 1, base_y + 10, offset_z + self.height - 1,
                AIR_BLOCK
            )
            # 放置基岩层
            await level.set_blocks(
                offset_x, base_y - 1, offset_z,
                offset_x + self.width - 1, base_y - 1, offset_z + self.height - 1,
                "minecraft:bedrock"
            )
            # 放置草地方块作为地面
            await level.set_blocks(
                offset_x, base_y, offset_z,
                offset_x + self.width - 1, base_y, offset_z + self.height - 1,
                "minecraft:grass_block"
            )

        # 放置农田
        print(f"放置 {len(self.farms)} 个农田...")
        for farm in self.farms:
            # 放置8个农田方块
            for x, y, z in farm.blocks:
                await level.set_block(x + offset_x, y + offset_y, z + offset_z, FARMLAND_BLOCK)
            # 在中间放置水源
            wx, wy, wz = farm.water_block
            await level.set_block(wx + offset_x, wy + offset_y, wz + offset_z, WATER_BLOCK)

        # 放置枢纽
        print(f"放置 {len(self.hubs)} 个枢纽...")
        for hub in self.hubs:
            # 平台（石头）
            for x, y, z in hub.platform_blocks:
                await level.set_block(x + offset_x, y + offset_y, z + offset_z, STONE_BLOCK)

            # 四角柱子（石头）
            for dy in range(1, hub.height):
                for dx, dz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    await level.set_block(
                        hub.x + dx + offset_x, hub.y + dy + offset_y, hub.z + dz + offset_z,
                        STONE_BLOCK
                    )

            # 屋顶（木块）
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    await level.set_block(
                        hub.x + dx + offset_x, hub.y + hub.height + offset_y, hub.z + dz + offset_z,
                        WOOD_BLOCK
                    )


        print("构建完成！")


async def demo():
    # 创建农业系统
    system = AgriculturalSystem(width=100, height=100)
    # 生成农田
    farms = system.generate_farms(min_count=50, max_count=70)
    print(f"生成了 {len(farms)} 个农田")
    # 优化枢纽位置并获取迭代历史
    hubs, history = system.optimize_hubs(k=3, return_history=True)
    print(f"优化了 {len(hubs)} 个枢纽位置")



    # 显示统计信息
    stats = system.calculate_statistics()
    print(f"\n统计信息:")
    print(f"  农田数量: {stats['farm_count']}")
    print(f"  枢纽数量: {stats['hub_count']}")
    print(f"  簇大小: {stats['cluster_sizes']}")
    print(f"  农田到枢纽总距离: {stats['total_farm_hub_distance']:.2f}")


    # 可选：连接到Minecraft并构建
    connect_mc = input("\n是否连接到Minecraft并构建？(y/n): ")
    if connect_mc.lower() == 'y':
        try:
            from pycraft import PyModClient
            client = PyModClient()
            await client.connect()
            level = client.overworld()

            # 获取玩家当前位置作为基准点
            players = await level.get_players()
            if players:
                player = players[0]
                pos = await player.get_pos()
                base_x, base_y, base_z = int(pos[0]), int(pos[1]), int(pos[2])
                print(f"以玩家位置为基准: ({base_x}, {base_y}, {base_z})")
                offset_y = base_y - system.base_y
            else:
                print("未找到玩家，将在原点构建")
                base_x, base_z, base_y = 0, 0, 0
                offset_y = 0

            # 首先构建地面和农田（清理区域）
            print("\n=== 构建地面和农田 ===")
            await system.build(
                level, clear_area=True,
                offset_x=base_x, offset_z=base_z, offset_y=offset_y
            )

            # 如果有迭代历史记录，进行迭代可视化
            if history and len(history) > 1:
                print("\n=== 开始K-means迭代过程可视化 ===")
                print("将在最终系统的同一位置按顺序展示三次迭代")
                print("每次迭代使用不同颜色的羊毛屋顶，最后展示最终系统（木块屋顶）")
                print("白色羊毛 -> 橙色羊毛 -> 洋红色羊毛 -> 木块屋顶")

                # 在最终系统的位置进行迭代可视化（使用相同的偏移坐标）
                await system.build_iterations_sequential(
                    level, history, max_iterations=3,
                    delay_seconds=3.0,  # 每次迭代间隔3秒
                    offset_x=base_x, offset_z=base_z, offset_y=offset_y
                )

                # 最后构建最终枢纽（覆盖最后一次迭代的枢纽，使用木块屋顶）
                print("\n=== 构建最终枢纽 ===")
                # 只构建枢纽，不清除区域，不重新构建农田
                for hub in system.hubs:
                    # 平台（石头）
                    for x, y, z in hub.platform_blocks:
                        await level.set_block(x + base_x, y + offset_y, z + base_z, STONE_BLOCK)

                    # 四角柱子（石头）
                    for dy in range(1, hub.height):
                        for dx, dz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                            await level.set_block(
                                hub.x + dx + base_x, hub.y + dy + offset_y, hub.z + dz + base_z,
                                STONE_BLOCK
                            )

                    # 屋顶（木块）
                    for dx in range(-1, 2):
                        for dz in range(-1, 2):
                            await level.set_block(
                                hub.x + dx + base_x, hub.y + hub.height + offset_y, hub.z + dz + base_z,
                                WOOD_BLOCK
                            )
                print("最终枢纽构建完成！")
            else:
                # 如果没有历史记录，最终系统已经构建完成（包括枢纽）
                pass

            await client.close()
            print("构建完成！")
        except Exception as e:
            print(f"连接Minecraft失败: {e}")
            print("请确保PyCraft服务器正在运行")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo())