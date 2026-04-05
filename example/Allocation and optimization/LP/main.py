import asyncio
import sys
import os
import numpy as np
from typing import Optional, Tuple
'''
防止路径识别不出来(ai)
'''
current_dir = os.path.dirname(os.path.abspath(__file__))
try:
    current_dir = os.fsdecode(os.fsencode(current_dir))
except (UnicodeEncodeError, UnicodeDecodeError):
    pass
if os.getcwd() != current_dir:
    try:
        os.chdir(current_dir)
    except Exception as e:
        print(f"警告: 无法更改工作目录到 {current_dir}: {e}")
sys.path.insert(0, current_dir)


try:
    from pycraft import PyModClient
    PYCRAFT_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入pycraft模块: {e}")
    print("将在控制台模式运行")
    PYCRAFT_AVAILABLE = False

from linear_programming import LinearProgrammingSolver
from farm_planner import FarmPlanner
from minecraft_visualizer import MinecraftVisualizer, ConsoleVisualizer

# 默认作物参数
DEFAULT_CROP_VALUES = {
    "小麦": {"value": 5.0, "work_time_per_harvest": 1.0},
    "胡萝卜": {"value": 8.0, "work_time_per_harvest": 1.5},
    "马铃薯": {"value": 7.0, "work_time_per_harvest": 1.2},
    "甜菜根": {"value": 10.0, "work_time_per_harvest": 2.0}
}

#没啥用 ai写的垃圾
def print_banner():
    """打印程序横幅"""
    print("\n" + "="*70)
    print("        种地问题线性规划求解与可视化")
    print("        在《我的世界》中展示最优农田规划")
    print("="*70)
def input_float(prompt: str, default: float = None, min_val: float = 0.0) -> float:
    """获取浮点数输入，支持默认值和最小值验证"""
    while True:
        try:
            user_input = input(f"{prompt}: ").strip()
            if not user_input and default is not None:
                return default
            value = float(user_input)
            if value <= min_val:
                print(f"错误: 值必须大于 {min_val}")
                continue
            return value
        except ValueError:
            print("错误: 请输入有效的数字")


def get_crop_value_and_worktime():
    """获取用户输入的作物价值和工作时长"""
    print("\n" + "="*70)
    print("作物参数设置")
    print("="*70)

    print("\n当前默认值:")
    for crop_name, values in DEFAULT_CROP_VALUES.items():
        print(f"  {crop_name}: 价值={values['value']}金币, 工作时长={values['work_time_per_harvest']}小时/次")

    choice = input("\n请选择: 1)使用默认值 2)自定义参数 [1/2]: ").strip()

    if choice == "1":
        print("使用默认参数")
        return None  # 使用默认值

    if choice != "2":
        print("输入无效，使用默认参数")
        return None

    crop_config = {}
    crops = ["小麦", "胡萝卜", "马铃薯", "甜菜根"]

    print("\n--- 自定义作物参数 ---")
    print("请输入每种作物的价值和工作时长（按Enter使用默认值）")

    for crop in crops:
        print(f"\n【{crop}】")
        default = DEFAULT_CROP_VALUES[crop]

        value = input_float(
            f"  价值（金币）",
            default=default["value"],
            min_val=0.0
        )

        work_time = input_float(
            f"  每次收获所需工作时长（小时）",
            default=default["work_time_per_harvest"],
            min_val=0.0
        )

        crop_config[crop] = {"value": value, "work_time_per_harvest": work_time}

    print("\n自定义参数设置完成:")
    for crop, config in crop_config.items():
        print(f"  {crop}: 价值={config['value']}金币, 工作时长={config['work_time_per_harvest']}小时/次")

    return crop_config


def print_problem_description(crop_config=None):
    """打印问题描述"""
    print("\n问题描述:")
    print("  1. 农田大小: 20个2×2地块（共80个方块）")
    print("  2. 作物选择: 小麦、胡萝卜、马铃薯、甜菜根")
    print("  3. 生长时间: 8000, 12000, 10000, 15000游戏刻")

    # 显示价值和工作时长（使用自定义参数或默认值）
    crops = ["小麦", "胡萝卜", "马铃薯", "甜菜根"]

    # 获取价值
    values = []
    for crop in crops:
        if crop_config and crop in crop_config and "value" in crop_config[crop]:
            values.append(crop_config[crop]["value"])
        else:
            values.append(DEFAULT_CROP_VALUES[crop]["value"])

    print(f"  4. 单位价值: {values[0]}, {values[1]}, {values[2]}, {values[3]}金币")

    # 获取工作时长
    work_times = []
    for crop in crops:
        if crop_config and crop in crop_config and "work_time_per_harvest" in crop_config[crop]:
            work_times.append(crop_config[crop]["work_time_per_harvest"])
        else:
            work_times.append(DEFAULT_CROP_VALUES[crop]["work_time_per_harvest"])

    print(f"  5. 工作时长: 小麦{work_times[0]}, 胡萝卜{work_times[1]}, 马铃薯{work_times[2]}, 甜菜根{work_times[3]}小时/次")

    print("  6. 周期长度: 24000游戏刻（1个Minecraft日）")
    print("  7. 总工作时长: 40小时/周期")
    print("  8. 目标: 最大化一个周期内的总收益")

#进入正题
async def solve_linear_programming(crop_config=None) -> Tuple[np.ndarray, float, FarmPlanner]:

    # 创建农田规划器
    planner = FarmPlanner(total_plots=50, period_ticks=24000, total_work_time=150.0,
                         crop_config=crop_config)

    # 构建线性规划问题
    c, A, b = planner.create_linear_program()

    print(f"\n线性规划问题:")
    print(f"  决策变量数: {len(c)}")
    print(f"  约束条件数: {len(b)}")
    print(f"  目标函数: max {c[0]:.1f}x1 + {c[1]:.1f}x2 + {c[2]:.1f}x3 + {c[3]:.1f}x4")
    print(f"  约束条件: 1) 地块总数 ≤ {planner.total_plots}; 2) 总工作时长 ≤ {planner.total_work_time}小时")

    # 求解线性规划
    print("\n求解线性规划...")
    solver = LinearProgrammingSolver(c, A, b)

    solution, objective, iterations = solver.solve()
    print(f"  求解成功！迭代次数: {len(iterations)}")
    print(f"  最优值: {objective:.2f}")

    # 打印解
    print("\n最优解:")
    crops = list(planner.crops.values())
    for i, (crop, value) in enumerate(zip(crops, solution)):
        print(f"  {crop.name}: {value:.2f}块")

    return solution, objective, planner



def allocate_farm_plots(planner: FarmPlanner, solution: np.ndarray) -> list:
    

    # 分配地块
    plots = planner.allocate_plots(solution)

    # 计算总价值
    total_value = planner.calculate_total_value(plots)

    # 控制台可视化
    planner.visualize_console(plots)

    return plots


async def connect_to_minecraft() -> Tuple[Optional[object], Optional[object], int, int, int]:

    try:
        # 尝试导入PyCraft
        from pycraft import PyModClient

        # 创建客户端
        client = PyModClient()
        print("连接PyCraft服务器...")
        await client.connect()

        # 获取主世界
        level = client.overworld()
        print("连接成功！")

        # 获取玩家位置作为基准
        players = await level.get_players()
        if players:
            player = players[0]
            pos = await player.get_pos()
            base_x, base_y, base_z = int(pos[0]), int(pos[1]), int(pos[2])
            print(f"  玩家位置: ({base_x}, {base_y}, {base_z})")
            print(f"  将以此位置为基准构建农田")
        else:
            base_x, base_y, base_z = 0, 60, 0
            print(f"  未找到玩家，使用默认位置: ({base_x}, {base_y}, {base_z})")

        return client, level, base_x, base_y, base_z

    except ImportError:
        print("错误: 未找到pycraft模块")
        print("  请确保PyCraft已正确安装")
        print("  将在控制台显示结果，跳过Minecraft可视化")
        return None, None, 0, 60, 0

    except Exception as e:
        print(f"连接失败: {e}")
        print("  请确保:")
        print("  1. Minecraft游戏正在运行")
        print("  2. PyCraft模组已安装")
        print("  3. PyCraft服务器正在运行（端口8086）")
        print("  将在控制台显示结果，跳过Minecraft可视化")
        return None, None, 0, 60, 0


async def visualize_in_minecraft(client, level, base_x, base_y, base_z,
                                plots, solution, objective):
    """在Minecraft中可视化"""
    print("\n" + "-"*50)
    print("步骤4: 在《我的世界》中构建农田")
    print("-"*50)

    if client is None or level is None:
        print("无法连接Minecraft，使用控制台可视化")
        await ConsoleVisualizer.visualize(plots, solution, objective)
        return

    try:
        # 创建可视化器
        visualizer = MinecraftVisualizer(client, base_x, base_y, base_z)

        # 开始构建（带动画效果）
        await visualizer.visualize(level, plots, solution, objective, animate=True)

        print("\n构建完成！")
        print("请进入游戏查看农田规划结果。")

        # 保持连接一段时间，让用户查看
        print("按Ctrl+C退出程序...")
        try:
            # 保持1小时，或直到用户中断
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            print("\n用户中断，关闭连接...")

        # 关闭连接
        await client.close()

    except Exception as e:
        print(f"构建过程中出错: {e}")
        print("切换到控制台可视化模式")
        await ConsoleVisualizer.visualize(plots, solution, objective)

        if client:
            await client.close()


async def run_console_mode(plots, solution, objective):
    """运行控制台模式（不连接Minecraft）"""
    print("\n" + "="*70)
    print("控制台模式")
    print("="*70)

    await ConsoleVisualizer.visualize(plots, solution, objective)

    print("\n提示:")
    print("  1. 要连接Minecraft，请确保:")
    print("     - Minecraft游戏正在运行")
    print("     - PyCraft模组已安装")
    print("     - 在游戏中输入 '/pycraft start' 启动服务器")
    print("  2. 然后重新运行此程序")
    print("  3. 或者手动构建:")
    print("     - 使用 '/give' 命令获取作物种子")
    print("     - 按照控制台显示的布局种植")

    input("\n按Enter键退出...")


async def main():
    """主函数"""
    # 打印横幅
    print_banner()

    # 获取作物参数配置
    crop_config = get_crop_value_and_worktime()

    # 打印问题描述（使用实际参数）
    print_problem_description(crop_config)

    try:
        # 步骤1: 求解线性规划
        solution, objective, planner = await solve_linear_programming(crop_config)

        # 步骤2: 分配农田地块
        plots = allocate_farm_plots(planner, solution)

        # 询问是否连接Minecraft
        print("\n" + "-"*50)
        print("可视化选项")
        print("-"*50)
        print("  1. 尝试连接Minecraft并构建（推荐）")
        print("  2. 仅使用控制台可视化")
        print("  3. 退出")

        choice = input("\n请选择 (1/2/3): ").strip()

        if choice == '3':
            print("退出程序")
            return

        if choice == '1':
            # 步骤3: 连接Minecraft
            client, level, base_x, base_y, base_z = await connect_to_minecraft()

            if client is not None and level is not None:
                # 步骤4: 在Minecraft中可视化
                await visualize_in_minecraft(client, level, base_x, base_y, base_z,
                                           plots, solution, objective)
            else:
                # 连接失败，使用控制台模式
                await run_console_mode(plots, solution, objective)

        else:  # choice == '2' 或其他
            # 使用控制台模式
            await run_console_mode(plots, solution, objective)

    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序出错: {e}")
        import traceback
        traceback.print_exc()
        input("\n按Enter键退出...")


if __name__ == "__main__":
    # 运行主程序，捕获所有异常
    try:
        asyncio.run(main())
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所需依赖: numpy, scipy")
        print("可以使用 pip install numpy scipy 安装")
        input("\n按Enter键退出...")
    except Exception as e:
        print(f"程序运行错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按Enter键退出...")