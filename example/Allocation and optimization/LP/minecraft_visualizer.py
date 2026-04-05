"""
《我的世界》可视化引擎 - 将农田规划结果可视化到Minecraft中
"""

import asyncio
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
import math
import numpy as np

from farm_planner import FarmPlot, FarmPlanner


@dataclass
class VisualizationConfig:
    """可视化配置"""
    plot_spacing: int = 5          # 地块间距（方块）增加到5以适应3×3农田
    path_width: int = 2            # 路径宽度
    fence_height: int = 2          # 围栏高度（1=地面，2=顶部）
    light_height: int = 3          # 光源高度（相对于地面）
    sign_height: int = 2           # 告示牌高度
    use_real_crops: bool = True    # 使用真实作物方块


class MinecraftVisualizer:
    """《我的世界》可视化引擎"""

    # 方块类型定义
    FARMLAND = "minecraft:farmland"
    WATER = "minecraft:water"
    GRASS_BLOCK = "minecraft:grass_block"
    DIRT = "minecraft:dirt"
    OAK_FENCE = "minecraft:oak_fence"
    OAK_PLANKS = "minecraft:oak_planks"
    OAK_SIGN = "minecraft:oak_sign"  # 告示牌
    TORCH = "minecraft:torch"
    AIR = "minecraft:air"
    STONE = "minecraft:stone"
    BEDROCK = "minecraft:bedrock"

    # 作物方块映射（使用基础方块类型）
    CROP_BLOCKS = {
        '小麦': "minecraft:wheat",        # 小麦作物
        '胡萝卜': "minecraft:carrots",    # 胡萝卜作物
        '马铃薯': "minecraft:potatoes",   # 马铃薯作物
        '甜菜根': "minecraft:beetroots"   # 甜菜根作物
    }

    def __init__(self, client, base_x: int = 0, base_y: int = 60, base_z: int = 0,
                 config: Optional[VisualizationConfig] = None):
        """
        初始化可视化引擎
        client: PyModClient实例
        base_x, base_y, base_z: 基准坐标
        config: 可视化配置
        """
        self.client = client
        self.base_x = base_x
        self.base_y = base_y
        self.base_z = base_z
        self.config = config or VisualizationConfig()

        # 作物方块选择
        self.crop_blocks = self.CROP_BLOCKS

    async def prepare_terrain(self, level, plots: List[FarmPlot], margin: int = 5):
        """
        准备地形：清理区域并创建平坦地面
        plots: 农田地块列表
        margin: 边界留白
        """
        print("准备地形...")

        # 计算需要清理的区域范围
        xs = [plot.x for plot in plots]
        zs = [plot.z for plot in plots]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)

        # 添加间距和边界
        min_x -= margin
        max_x += margin + 3  # 地块宽度+间距
        min_z -= margin
        max_z += margin + 3

        # 转换为世界坐标
        world_min_x = self.base_x + min_x
        world_max_x = self.base_x + max_x
        world_min_z = self.base_z + min_z
        world_max_z = self.base_z + max_z

        # 计算高度范围（清除地面以上3格空间）
        ground_y = self.base_y
        clear_min_y = ground_y
        clear_max_y = ground_y + 5  # 留出空间给围栏和作物

        # 清除区域（空气方块）
        print(f"  清除区域: ({world_min_x}, {clear_min_y}, {world_min_z}) "
              f"到 ({world_max_x}, {clear_max_y}, {world_max_z})")

        await level.set_blocks(
            world_min_x, clear_min_y, world_min_z,
            world_max_x, clear_max_y, world_max_z,
            self.AIR
        )

        # 创建基岩层（防止掉落）
        await level.set_blocks(
            world_min_x, ground_y - 1, world_min_z,
            world_max_x, ground_y - 1, world_max_z,
            self.BEDROCK
        )

        # 创建草地方块地面
        await level.set_blocks(
            world_min_x, ground_y, world_min_z,
            world_max_x, ground_y, world_max_z,
            self.GRASS_BLOCK
        )

        print(f"  地形准备完成")

        # 返回实际使用的区域范围
        return {
            'min_x': world_min_x,
            'max_x': world_max_x,
            'min_z': world_min_z,
            'max_z': world_max_z,
            'ground_y': ground_y
        }

    async def create_farm_plot(self, level, plot: FarmPlot, grid_info=None):
        """
        创建单个农田地块
        包括：耕地、水、作物、围栏
        grid_info: 可选网格信息字典，包含：
            rows: 总行数
            cols_per_row: 每行列数（通常为4）
            plot_spacing: 地块间距
            min_x: 最小x坐标
            min_z: 最小z坐标
        """
        # 世界坐标
        world_x = self.base_x + plot.x
        world_z = self.base_z + plot.z
        ground_y = self.base_y + plot.y

        # 1. 创建耕地（3×3地块）
        print(f"  创建农田地块 #{plot.index}: ({plot.x}, {plot.z}) - {plot.crop.name}")

        # 耕地方块（3×3）
        for dx in range(3):
            for dz in range(3):
                await level.set_block(
                    world_x + dx, ground_y, world_z + dz,
                    self.FARMLAND
                )

        # 2. 在中心放置水（保持耕地湿润）
        water_y = ground_y  # 与耕地同一层
        await level.set_block(world_x + 1, water_y, world_z + 1, self.WATER)

        # 3. 种植作物（在耕地上方）
        crop_block = self.crop_blocks.get(plot.crop.name, "minecraft:wheat")
        crop_y = ground_y + 1  # 耕地上方1格

        for dx in range(3):
            for dz in range(3):
                # 跳过中心有水的位置
                if dx == 1 and dz == 1:
                    continue  # 这是水的位置

                await level.set_block(
                    world_x + dx, crop_y, world_z + dz,
                    crop_block
                )

        # 4. 创建围栏（现在由create_outer_fence统一生成）
        # 跳过单个地块的围栏生成，避免重复和连接问题
        # 短暂暂停，避免请求过快
        await asyncio.sleep(0.05)

    def _get_crop_marker(self, crop_name: str) -> str:
        """获取作物标记方块（彩色羊毛）"""
        markers = {
            '小麦': "minecraft:yellow_wool",
            '胡萝卜': "minecraft:orange_wool",
            '马铃薯': "minecraft:brown_wool",
            '甜菜根': "minecraft:red_wool"
        }
        return markers.get(crop_name, "minecraft:white_wool")

    async def create_paths(self, level, plots: List[FarmPlot], area_info: dict):
        """
        创建农田之间的路径
        """
        print("创建路径...")

        ground_y = area_info['ground_y']
        path_y = ground_y  # 路径与地面同一层

        # 计算需要路径的区域
        xs = [plot.x for plot in plots]
        zs = [plot.z for plot in plots]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)

        # 扩展为包含所有地块的网格
        plots_per_row = 5  # 与farm_planner中一致（5×6网格）
        plot_spacing = self.config.plot_spacing

        # 创建行间路径
        rows = math.ceil(len(plots) / plots_per_row)
        for row in range(rows - 1):
            row_z = min_z + row * plot_spacing

            # 路径位于两行地块之间（3×3农田，围栏在z+3位置）
            path_z = row_z + 3  # 路径在地块之间

            for col in range(plots_per_row + 1):
                path_x = min_x + col * plot_spacing

                # 创建路径方块（草方块）
                world_x = self.base_x + path_x
                world_z = self.base_z + path_z

                # 检查是否在区域内
                if (area_info['min_x'] <= world_x <= area_info['max_x'] and
                    area_info['min_z'] <= world_z <= area_info['max_z']):

                    # 创建2格宽的路径（使用草方块保持地面一致）
                    for dw in range(self.config.path_width):
                        await level.set_block(
                            world_x + dw, path_y, world_z,
                            self.GRASS_BLOCK
                        )

        # 创建列间路径
        for col in range(plots_per_row - 1):
            col_x = min_x + col * plot_spacing

            # 路径位于两列地块之间（3×3农田，围栏在x+3位置）
            path_x = col_x + 3

            for row in range(rows + 1):
                path_z = min_z + row * plot_spacing

                world_x = self.base_x + path_x
                world_z = self.base_z + path_z

                if (area_info['min_x'] <= world_x <= area_info['max_x'] and
                    area_info['min_z'] <= world_z <= area_info['max_z']):

                    # 创建2格宽的路径（使用草方块保持地面一致）
                    for dw in range(self.config.path_width):
                        await level.set_block(
                            world_x, path_y, world_z + dw,
                            self.GRASS_BLOCK
                        )

        print(f"  路径创建完成")

    async def create_sign_board(self, level, area_info: dict, solution: np.ndarray,
                               objective: float, plots: List[FarmPlot]):
        """
        创建单个告示牌显示种植方案
        使用Minecraft告示牌方块显示农作物信息
        """
        print("创建告示牌...")

        ground_y = area_info['ground_y']

        # 告示牌位置（在农田区域右侧）
        sign_x = area_info['max_x'] + 5
        sign_z = area_info['min_z'] + 5  # 稍微靠中间一些
        sign_y = ground_y + 1  # 地面以上1格

        # 计算作物分配统计
        crop_counts = {}
        for plot in plots:
            crop_name = plot.crop.name
            crop_counts[crop_name] = crop_counts.get(crop_name, 0) + 1

        # 创建告示牌文本内容（最多4行，每行约15个字符）
        # 第一行：标题
        sign_lines = ["农田规划"]

        # 第二行：总地块和总收益（简化显示）
        sign_lines.append(f"地:{len(plots)} 收:{objective:.0f}")

        # 定义固定的作物顺序和简称
        crop_order = [
            ("小麦", "麦"),
            ("胡萝卜", "萝"),
            ("马铃薯", "薯"),
            ("甜菜根", "甜")
        ]

        # 收集有分配的作物信息
        crop_items = []
        for crop_name, short_name in crop_order:
            if crop_name in crop_counts and crop_counts[crop_name] > 0:
                count = crop_counts[crop_name]
                crop_items.append(f"{short_name}:{count}")

        # 将作物信息分配到两行
        if len(crop_items) > 0:
            # 第一行作物信息（最多两个）
            if len(crop_items) > 0:
                line1 = " ".join(crop_items[:2])  # 前两个作物
                sign_lines.append(line1)

            # 第二行作物信息（如果有的话）
            if len(crop_items) > 2:
                line2 = " ".join(crop_items[2:4])  # 第三、四个作物
                sign_lines.append(line2)
            elif len(crop_items) == 2 and len(sign_lines) < 4:
                # 如果只有2个作物，第四行可以显示其他信息或留空
                sign_lines.append("最优规划")

        # 确保不超过4行
        sign_lines = sign_lines[:4]

        print(f"  告示牌内容: {sign_lines}")

        # 创建单个告示牌方块（立在地上的告示牌）
        try:
            # 尝试创建告示牌，朝向南方
            await level.set_block(
                sign_x, sign_y, sign_z,
                self.OAK_SIGN
            )
            print(f"  告示牌位置: [{sign_x}, {sign_y}, {sign_z}]")
            print(f"  内容预览:")
            for line in sign_lines:
                print(f"    {line}")
        except Exception as e:
            print(f"  创建告示牌失败: {e}")
            # 使用木板作为后备
            await level.set_block(
                sign_x, sign_y, sign_z,
                self.OAK_PLANKS
            )
            print(f"  已创建木板代替告示牌")

        print(f"  告示牌创建完成")
        print(f"  注: 由于API限制，告示牌文本需要在游戏中手动编辑")


    async def visualize(self, level, plots: List[FarmPlot], solution: np.ndarray,
                       objective: float, animate: bool = False):
        """
        主可视化函数
        plots: 农田地块列表
        solution: 线性规划解
        objective: 目标函数值
        animate: 是否使用动画效果
        """
        print("\n" + "="*60)
        print("开始在《我的世界》中构建农田...")
        print("="*60)

        start_time = time.time()

        # 1. 准备地形
        area_info = await self.prepare_terrain(level, plots)

        # 2. 创建农田地块
        print(f"\n创建{len(plots)}个农田地块...")

        # 计算网格信息用于生成最外侧围栏
        xs = [plot.x for plot in plots]
        zs = [plot.z for plot in plots]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)

        # 从create_paths函数中获取网格参数
        plots_per_row = 5  # 与farm_planner中一致（5×6网格）
        plot_spacing = self.config.plot_spacing
        rows = math.ceil(len(plots) / plots_per_row)

        grid_info = {
            'rows': rows,
            'cols_per_row': plots_per_row,
            'plot_spacing': plot_spacing,
            'min_x': min_x,
            'min_z': min_z,
            'all_plots': plots  # 用于计算最后一列
        }

        for i, plot in enumerate(plots):
            if animate:
                # 动画效果：逐个创建
                print(f"  创建地块 {i+1}/{len(plots)}...")
            await self.create_farm_plot(level, plot, grid_info)

            if animate and i < len(plots) - 1:
                # 短暂暂停，产生动画效果
                await asyncio.sleep(0.2)

        # 3. 创建外围围栏
        await self.create_outer_fence(level, plots, grid_info)

        # 4. 创建路径
        await self.create_paths(level, plots, area_info)

        # 4. 创建告示牌（单个，显示作物信息）
        await self.create_sign_board(level, area_info, solution, objective, plots)

        # 5. 不再创建图例（根据用户要求删除四个独立田块）

        # 6. 添加照明（确保整个区域亮度充足） - 已简化，移除光源
        # await self._add_lighting(level, area_info)

        elapsed_time = time.time() - start_time
        print(f"\n" + "="*60)
        print(f"农田构建完成！耗时: {elapsed_time:.1f}秒")
        print(f"基准坐标: ({self.base_x}, {self.base_y}, {self.base_z})")
        print("="*60)

    async def create_outer_fence(self, level, plots: List[FarmPlot], grid_info: dict):
        """
        创建完整的外围围栏框住整个农田区域
        plots: 农田地块列表
        grid_info: 网格信息字典
        """
        print("创建外围围栏...")

        # 计算整个农田区域的外围边界
        xs = [plot.x for plot in plots]
        zs = [plot.z for plot in plots]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)

        # 每个地块是3×3，围栏应该在地块外围1格
        # 西边界：min_x - 1
        # 东边界：max_x + 3 (因为地块宽3格，从min_x到min_x+2，所以东边界在min_x+3)
        # 南边界：min_z - 1
        # 北边界：max_z + 3

        fence_y = self.base_y + 1  # 地面以上1格（与create_farm_plot中的fence_y一致）

        # 计算围栏的实际世界坐标
        west_x = self.base_x + min_x - 1
        east_x = self.base_x + max_x + 3
        south_z = self.base_z + min_z - 1
        north_z = self.base_z + max_z + 3

        # 计算围栏长度（地块数量 × 地块宽度）
        plots_per_row = grid_info['cols_per_row']
        rows = grid_info['rows']

        # 总宽度：列数 × 地块间距，但最后一块地没有右侧间距
        total_width = plots_per_row * 3 + (plots_per_row - 1) * (grid_info['plot_spacing'] - 3)
        total_depth = rows * 3 + (rows - 1) * (grid_info['plot_spacing'] - 3)

        # 生成西边界围栏（从南到北）
        for dz in range(total_depth + 2):  # +2 因为包含角落
            z = south_z + dz
            await level.set_block(west_x, fence_y, z, self.OAK_FENCE)

        # 生成东边界围栏（从南到北）
        for dz in range(total_depth + 2):
            z = south_z + dz
            await level.set_block(east_x, fence_y, z, self.OAK_FENCE)

        # 生成南边界围栏（从西到东）
        for dx in range(total_width + 2):
            x = west_x + dx
            await level.set_block(x, fence_y, south_z, self.OAK_FENCE)

        # 生成北边界围栏（从西到东）
        for dx in range(total_width + 2):
            x = west_x + dx
            await level.set_block(x, fence_y, north_z, self.OAK_FENCE)

        print(f"  外围围栏完成: 西({west_x}) 东({east_x}) 南({south_z}) 北({north_z})")
        print(f"  围栏尺寸: {total_width + 2}×{total_depth + 2}")

    async def _add_lighting(self, level, area_info: dict):
        """添加照明（已简化，不添加光源）"""
        print("跳过照明添加（简化可视化）...")
        # 简化可视化：不需要光源


# 简化版可视化（不连接Minecraft）
class ConsoleVisualizer:
    """控制台可视化器（用于测试）"""

    @staticmethod
    async def visualize(plots: List[FarmPlot], solution: np.ndarray, objective: float):
        """
        在控制台显示可视化结果
        """
        print("\n" + "="*60)
        print("控制台可视化结果")
        print("="*60)

        print(f"总地块数: {len(plots)}")
        print(f"总收益: {objective:.1f}金币")

        # 作物统计
        crop_counts = {}
        for plot in plots:
            crop_name = plot.crop.name
            crop_counts[crop_name] = crop_counts.get(crop_name, 0) + 1

        print("\n作物分配:")
        for crop_name, count in crop_counts.items():
            print(f"  {crop_name}: {count}块")

        print("\n线性规划解:")
        crops = list(FarmPlanner.CROPS.values())
        for i, value in enumerate(solution):
            print(f"  {crops[i].name}: {value:.2f}")

        print("\n农田布局预览:")
        print("  [W]小麦  [C]胡萝卜  [P]马铃薯  [B]甜菜根")
        print("  □ 耕地  ~ 水（中心）  # 围栏")

        # 简化的ASCII布局
        if plots:
            # 计算网格
            xs = sorted(set(plot.x for plot in plots))
            zs = sorted(set(plot.z for plot in plots))

            # 创建字符映射
            crop_chars = {
                '小麦': 'W',
                '胡萝卜': 'C',
                '马铃薯': 'P',
                '甜菜根': 'B'
            }

            # 创建网格
            grid = {}
            for plot in plots:
                char = crop_chars.get(plot.crop.name, '?')
                grid[(plot.x, plot.z)] = char

            # 打印网格
            print("\n  ", end='')
            for x in xs:
                print(f" {x:2}", end='')
            print()

            for z in zs:
                print(f"  {z:2}", end='')
                for x in xs:
                    char = grid.get((x, z), ' ')
                    print(f"  {char}", end='')
                print()

        print("\n" + "="*60)
        print("可视化完成（控制台模式）")
        print("="*60)