"""
农田规划模块 - 将线性规划解转换为具体的农田布局
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np
import math


@dataclass
class Crop:
    """作物定义"""
    name: str                    # 作物名称
    growth_time: int            # 生长时间（游戏刻）
    work_time_per_harvest: float # 每次收获所需工作时长（小时）
    value: float                # 单位价值（金币）
    block_type: str             # Minecraft方块类型
    mature_block_type: str      # 成熟作物方块类型（可选，如果不同）
    color: str                  # 显示颜色（用于控制台输出）
    max_growth_stage: int = 7   # 最大生长阶段（0-7）


@dataclass
class FarmPlot:
    """单个农田地块"""
    x: int           # 地块左上角x坐标
    z: int           # 地块左上角z坐标
    y: int           # 地块高度
    crop: Crop       # 种植的作物
    index: int       # 地块索引
    growth_stage: int = 7  # 生长阶段（默认完全成熟）


class FarmPlanner:
    """农田规划器"""

    # 真实的Minecraft作物定义
    CROPS = {
        'wheat': Crop(
            name='小麦',
            growth_time=8000,      # 约0.5个Minecraft日
            work_time_per_harvest=1.0,  # 每次收获需要1小时
            value=5.0,            # 单位价值
            block_type='minecraft:wheat[age=0]',     # 刚种植的小麦
            mature_block_type='minecraft:wheat[age=7]',  # 完全成熟的小麦
            color='yellow',
            max_growth_stage=7
        ),
        'carrot': Crop(
            name='胡萝卜',
            growth_time=12000,     # 约0.75个Minecraft日
            work_time_per_harvest=1.5,  # 每次收获需要1.5小时
            value=8.0,
            block_type='minecraft:carrots[age=0]',
            mature_block_type='minecraft:carrots[age=7]',
            color='orange',
            max_growth_stage=7
        ),
        'potato': Crop(
            name='马铃薯',
            growth_time=10000,     # 约0.625个Minecraft日
            work_time_per_harvest=1.2,  # 每次收获需要1.2小时
            value=7.0,
            block_type='minecraft:potatoes[age=0]',
            mature_block_type='minecraft:potatoes[age=7]',
            color='brown',
            max_growth_stage=7
        ),
        'beetroot': Crop(
            name='甜菜根',
            growth_time=15000,     # 约0.94个Minecraft日
            work_time_per_harvest=2.0,  # 每次收获需要2小时
            value=10.0,
            block_type='minecraft:beetroots[age=0]',
            mature_block_type='minecraft:beetroots[age=3]',  # 甜菜根只有4个阶段
            color='red',
            max_growth_stage=3
        )
    }

    def __init__(self, total_plots: int = 20, period_ticks: int = 24000, total_work_time: float = 40.0,
                 crop_config=None):
        """
        初始化农田规划器
        total_plots: 总地块数
        period_ticks: 周期长度（游戏刻）
        total_work_time: 每个周期可投入的总工作时长（小时）
        crop_config: 可选字典，格式为：
            {
                "小麦": {"value": 5.0, "work_time_per_harvest": 1.0},
                "胡萝卜": {"value": 8.0, "work_time_per_harvest": 1.5},
                ...
            }
        用于覆盖CROPS中的对应参数
        """
        self.total_plots = total_plots
        self.period_ticks = period_ticks
        self.total_work_time = total_work_time
        self.work_times_per_period = None  # 每种作物每个周期每块地的工作时长

        # 应用作物配置
        self.crops = self._apply_crop_config(crop_config)

        # 验证参数
        if total_plots <= 0:
            raise ValueError("总地块数必须大于0")
        if period_ticks <= 0:
            raise ValueError("周期长度必须大于0")
        if total_work_time <= 0:
            raise ValueError("总工作时长必须大于0")

    def _apply_crop_config(self, crop_config):
        """应用作物配置覆盖，返回更新后的作物字典"""
        # 创建CROPS的深拷贝（实际上需要复制Crop对象）
        import copy
        crops_copy = {}
        for key, crop in self.CROPS.items():
            crops_copy[key] = copy.copy(crop)  # 浅拷贝Crop对象

        if not crop_config:
            return crops_copy

        # 映射中文作物名到英文键
        chinese_to_english = {
            "小麦": "wheat",
            "胡萝卜": "carrot",
            "马铃薯": "potato",
            "甜菜根": "beetroot"
        }

        for chinese_name, config in crop_config.items():
            english_key = chinese_to_english.get(chinese_name)
            if english_key and english_key in crops_copy:
                crop = crops_copy[english_key]
                if "value" in config:
                    crop.value = config["value"]
                if "work_time_per_harvest" in config:
                    crop.work_time_per_harvest = config["work_time_per_harvest"]

        return crops_copy

    def create_linear_program(self) -> Tuple[List[float], List[List[float]], List[float]]:
        """
        创建种地问题的线性规划模型
        返回: (目标函数系数c, 约束矩阵A, 约束右端项b)
        """
        crops = list(self.crops.values())

        # 计算每种作物在一个周期内的收获次数
        harvest_counts = []
        effective_values = []
        work_times = []

        for crop in crops:
            # 计算收获次数（向下取整）
            harvests = self.period_ticks // crop.growth_time
            if harvests == 0:
                # 如果生长时间超过周期长度，至少可以收获一次（在周期结束时）
                harvests = 1
            harvest_counts.append(harvests)

            # 计算有效价值（单位价值 × 收获次数）
            effective_value = crop.value * harvests
            effective_values.append(effective_value)

            # 计算每个周期每块地的总工作时长（每次收获所需时间 × 收获次数）
            work_time_per_period = crop.work_time_per_harvest * harvests
            work_times.append(work_time_per_period)

            print(f"  {crop.name}: 生长时间={crop.growth_time}刻, "
                  f"单位价值={crop.value}, 收获次数={harvests}, "
                  f"有效价值={effective_value}, 工作时长={work_time_per_period:.1f}小时")

        # 存储工作时长供后续使用
        self.work_times_per_period = work_times

        # 目标函数系数（最大化总收益）
        c = effective_values

        # 约束矩阵：地块总数约束 + 工作时间约束
        # 约束1: x1 + x2 + x3 + x4 ≤ total_plots
        # 约束2: work_time1*x1 + work_time2*x2 + work_time3*x3 + work_time4*x4 ≤ total_work_time
        A = [[1] * len(crops), work_times]

        # 约束右端项
        b = [self.total_plots, self.total_work_time]

        print(f"线性规划模型:")
        print(f"  决策变量: {[crop.name for crop in crops]}")
        print(f"  目标函数系数: {c}")
        print(f"  约束1: {' + '.join([f'x{i+1}' for i in range(len(crops))])} ≤ {self.total_plots}")
        print(f"  约束2: {' + '.join([f'{work_times[i]:.1f}x{i+1}' for i in range(len(crops))])} ≤ {self.total_work_time}")

        return c, A, b

    def allocate_plots(self, solution: np.ndarray,
                      start_x: int = 0, start_z: int = 0, start_y: int = 0) -> List[FarmPlot]:
        """
        根据线性规划解分配具体的地块
        solution: 线性规划解（每种作物的地块数量）
        start_x, start_z, start_y: 起始坐标
        返回: 农田地块列表
        """
        crops = list(self.crops.values())

        # 验证解的长度
        if len(solution) != len(crops):
            raise ValueError(f"解的长度{len(solution)}与作物数量{len(crops)}不匹配")

        # 计算每种作物分配的地块数（四舍五入到最接近的整数）
        allocated = []
        total_allocated = 0

        for i, x in enumerate(solution):
            # 四舍五入到最接近的整数
            count = int(round(x))
            if count < 0:
                count = 0
            allocated.append(count)
            total_allocated += count

            print(f"  {crops[i].name}: 分配{count}块（原始解: {x:.2f}）")

        # 调整总数以匹配总地块数
        if total_allocated != self.total_plots:
            print(f"调整地块分配: 总数{total_allocated} → 目标{self.total_plots}")

            if total_allocated > self.total_plots:
                # 需要减少地块数，按比例减少
                scale = self.total_plots / total_allocated
                allocated = [int(count * scale) for count in allocated]

                # 如果仍然超过，从最多的作物开始逐个减少
                while sum(allocated) > self.total_plots:
                    max_idx = np.argmax(allocated)
                    if allocated[max_idx] > 0:
                        allocated[max_idx] -= 1

            else:  # total_allocated < self.total_plots
                # 需要增加地块数，按比例增加
                # 优先分配给有效价值高的作物
                crops_with_values = [(i, crops[i].value)
                                   for i in range(len(crops))]
                crops_with_values.sort(key=lambda x: x[1], reverse=True)

                remaining = self.total_plots - sum(allocated)
                for i, _ in crops_with_values:
                    if remaining <= 0:
                        break
                    allocated[i] += 1
                    remaining -= 1

        # 调整工作时间约束
        # 计算每种作物每个周期每块地的工作时长
        work_times = []
        for crop in crops:
            harvests = self.period_ticks // crop.growth_time
            if harvests == 0:
                harvests = 1
            work_time_per_period = crop.work_time_per_harvest * harvests
            work_times.append(work_time_per_period)

        total_work = sum(allocated[i] * work_times[i] for i in range(len(crops)))
        print(f"调整后总工作时长: {total_work:.1f}小时 (限制: {self.total_work_time}小时)")

        # 如果总工作时长超过限制，减少地块
        while total_work > self.total_work_time:
            # 找到工作贡献最大的作物（allocated[i] * work_times[i]最大）
            contributions = [(i, allocated[i] * work_times[i]) for i in range(len(crops)) if allocated[i] > 0]
            if not contributions:
                break
            # 选择贡献最大的作物
            i, _ = max(contributions, key=lambda x: x[1])
            allocated[i] -= 1
            total_work -= work_times[i]
            print(f"  减少1块{crops[i].name}，总工作时长降至{total_work:.1f}小时")

        # 如果总工作时长未超限且还有剩余工作时间，可以增加地块（但地块总数可能已达标，暂时不增加）

        # 创建网格布局
        plots = []
        plot_index = 0

        # 网格参数：每个地块占5×5空间（包含3×3农田和走道）
        plots_per_row = 5  # 每行5个地块（5×6网格）
        plot_spacing = 5   # 地块间距增加到5以适应3×3农田

        for crop_idx, crop in enumerate(crops):
            for _ in range(allocated[crop_idx]):
                # 计算网格位置
                row = plot_index // plots_per_row
                col = plot_index % plots_per_row

                # 计算坐标（考虑间距）
                x = start_x + col * plot_spacing
                z = start_z + row * plot_spacing
                y = start_y

                # 创建地块（默认完全成熟）
                plot = FarmPlot(
                    x=x, z=z, y=y,
                    crop=crop,
                    index=plot_index,
                    growth_stage=crop.max_growth_stage  # 完全成熟
                )
                plots.append(plot)
                plot_index += 1

        print(f"地块分配完成: 总共{len(plots)}块田地")
        print(f"布局: {plots_per_row}列 × {math.ceil(len(plots)/plots_per_row)}行")

        return plots

    def calculate_total_value(self, plots: List[FarmPlot]) -> float:
        """计算农田的总价值（基于作物类型和数量）"""
        total_value = 0.0
        crop_counts = {}

        for plot in plots:
            crop_name = plot.crop.name
            crop_counts[crop_name] = crop_counts.get(crop_name, 0) + 1

            # 计算单个地块的价值（考虑收获次数）
            harvests = self.period_ticks // plot.crop.growth_time
            if harvests == 0:
                harvests = 1
            total_value += plot.crop.value * harvests

        print("\n作物分配统计:")
        for crop_name, count in crop_counts.items():
            crop = next(c for c in self.crops.values() if c.name == crop_name)
            harvests = self.period_ticks // crop.growth_time
            if harvests == 0:
                harvests = 1
            value_per_plot = crop.value * harvests
            total_crop_value = value_per_plot * count

            print(f"  {crop_name}: {count}块, "
                  f"每块{value_per_plot:.1f}金币, "
                  f"小计{total_crop_value:.1f}金币")

        print(f"总收益: {total_value:.1f}金币")

        return total_value

    def visualize_console(self, plots: List[FarmPlot], width: int = 60, height: int = 30):
        """
        在控制台可视化农田布局
        plots: 农田地块列表
        width, height: 控制台显示尺寸
        """
        if not plots:
            print("没有农田地块可显示")
            return

        # 找到坐标范围
        xs = [plot.x for plot in plots]
        zs = [plot.z for plot in plots]
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)

        # 扩展范围以包含整个地块（3×3）
        min_x -= 1
        max_x += 3
        min_z -= 1
        max_z += 3

        # 计算缩放比例
        world_width = max_x - min_x + 1
        world_depth = max_z - min_z + 1

        # 创建字符画布
        canvas = [[' ' for _ in range(width)] for _ in range(height)]

        # 坐标映射函数
        def map_x(x):
            return int(((x - min_x) / world_width) * (width - 1))

        def map_z(z):
            return int(((z - min_z) / world_depth) * (height - 1))

        # 绘制每个地块
        for plot in plots:
            # 使用作物名称的首字母作为标记
            marker = plot.crop.name[0]  # 中文首字
            color_code = {
                '小麦': 'W',    # Wheat
                '胡萝卜': 'C',  # Carrot
                '马铃薯': 'P',  # Potato
                '甜菜根': 'B'   # Beetroot
            }.get(plot.crop.name, '?')

            # 在地块中心位置标记（3×3农田，中心在(1.5, 1.5)）
            center_x = plot.x + 1.5
            center_z = plot.z + 1.5

            canvas_x = map_x(center_x)
            canvas_z = map_z(center_z)

            if 0 <= canvas_x < width and 0 <= canvas_z < height:
                canvas[canvas_z][canvas_x] = color_code

        # 绘制边框
        border_x = map_x(min_x)
        border_z = map_z(min_z)
        border_width = map_x(max_x) - border_x + 1
        border_height = map_z(max_z) - border_z + 1

        for i in range(border_width):
            if 0 <= border_x + i < width:
                if 0 <= border_z < height:
                    canvas[border_z][border_x + i] = '-'
                if 0 <= border_z + border_height - 1 < height:
                    canvas[border_z + border_height - 1][border_x + i] = '-'

        for i in range(border_height):
            if 0 <= border_z + i < height:
                if 0 <= border_x < width:
                    canvas[border_z + i][border_x] = '|'
                if 0 <= border_x + border_width - 1 < width:
                    canvas[border_z + i][border_x + border_width - 1] = '|'

        # 添加角标记
        if 0 <= border_z < height and 0 <= border_x < width:
            canvas[border_z][border_x] = '+'
        if 0 <= border_z < height and 0 <= border_x + border_width - 1 < width:
            canvas[border_z][border_x + border_width - 1] = '+'
        if 0 <= border_z + border_height - 1 < height and 0 <= border_x < width:
            canvas[border_z + border_height - 1][border_x] = '+'
        if 0 <= border_z + border_height - 1 < height and 0 <= border_x + border_width - 1 < width:
            canvas[border_z + border_height - 1][border_x + border_width - 1] = '+'

        # 转换为字符串
        print("\n农田布局（控制台视图）:")
        print("  W:小麦  C:胡萝卜  P:马铃薯  B:甜菜根")
        print("  " + "-" * width)

        for row in canvas:
            print("  " + ''.join(row))

        print("  " + "-" * width)


# 测试函数
def test_farm_planner():
    """测试农田规划器"""
    print("=== 测试农田规划器 ===")

    # 创建农田规划器
    planner = FarmPlanner(total_plots=20, period_ticks=24000)

    # 创建线性规划问题
    c, A, b = planner.create_linear_program()

    # 模拟一个解
    test_solution = np.array([0.0, 20.0, 0.0, 0.0])

    # 分配地块
    plots = planner.allocate_plots(test_solution)

    # 计算总价值
    total_value = planner.calculate_total_value(plots)

    # 控制台可视化
    planner.visualize_console(plots)

    return plots, total_value


if __name__ == "__main__":
    test_farm_planner()