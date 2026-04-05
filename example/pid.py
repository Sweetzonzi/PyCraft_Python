import asyncio
from pycraft import PyModClient

# 定义一个三维向量类，用于简化坐标运算
class Vec3:
    __slots__ = ("x", "y", "z") # 优化内存使用

    def __init__(self, x: float, y: float, z: float):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    # 重载加法运算符 (+)
    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    # 重载减法运算符 (-)
    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    # 重载乘法运算符 (*)，用于缩放向量
    def __mul__(self, scalar: float):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    # 计算向量模长（欧几里得距离）
    def length(self):
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    # 向量归一化，即将长度变为 1，但方向不变
    def normalize(self):
        l = self.length()
        if l == 0:
            return Vec3(0, 0, 0)
        return Vec3(self.x / l, self.y / l, self.z / l)

    def tuple(self):
        return (self.x, self.y, self.z)

    def __repr__(self):
        return f"Vec3({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

# 数值限幅函数：确保变量不会超过指定的范围
def clamp(v, limit):
    if v > limit: return limit
    if v < -limit: return -limit
    return v

# 向量限幅函数：限制向量的总长度，防止移动过快
def limit_vec(v, max_len) -> Vec3:
    length = v.length()
    if length > max_len:
        s = max_len / length # 计算缩放比例
        return v * s
    return v

async def main():
    mc = PyModClient()
    await mc.connect()
    try:
        overworld = mc.overworld()
        players = await overworld.get_players()
        player = players[0]
        
        # 设置玩家视角为第三人称
        await player.set_perspective(1)
        p_x, p_y, p_z = await player.get_pos()
        
        # 在玩家位置生成一个追踪目标（小猪）
        pig = await overworld.spawn_entity(
            "minecraft:pig",
            p_x, p_y, p_z
        )

        # PID控制器参数调节
        Kp = 0.2   # 比例系数
        Ki = 0.05  # 积分系数
        Kd = 0.1   # 微分系数

        # 初始化控制状态
        integral = Vec3(0,0,0)      # 误差累积（积分项）
        prev_error = Vec3(0,0,0)    # 上一帧的误差（用于计算微分项）
        derivative = Vec3(0,0,0)    # 误差变化率（微分项）

        dt = 0.05              # 循环步长（20次/秒，对应 Minecraft 的 Tick）
        integral_limit = 5     # 积分限幅，防止积分饱和
        output_limit = 0.3     # 每一帧允许的最大位移

        trajectory = []  # 存储玩家位置历史
        max_trajectory_points = 30  # 最多保留30个点（约1.5秒）

        # 主循环：持续追逐
        while True:
            # 1. 获取当前位置信息
            pig_x, pig_y, pig_z = await pig.get_pos()
            player_x, player_y, player_z = await player.get_pos()
            
            # 2. 计算误差 (Error) = 目标位置 - 玩家当前位置
            error = Vec3(pig_x - player_x, pig_y - player_y, pig_z - player_z)

            # P（Proportional）：直接乘误差，误差越大，推力越大
            # I（Integral）：累加误差。随时间增加，如果一直追不上，推力会越来越大
            integral.x += error.x * dt
            integral.y += error.y * dt
            integral.z += error.z * dt

            # 限制积分
            integral.x = clamp(integral.x, integral_limit)
            integral.y = clamp(integral.y, integral_limit)
            integral.z = clamp(integral.z, integral_limit)

            # D（Derivative）：计算误差的变化。预测未来，如果快追上了，D项会产生反向作用力防止撞击
            derivative.x = (error.x - prev_error.x) / dt
            derivative.y = (error.y - prev_error.y) / dt
            derivative.z = (error.z - prev_error.z) / dt

            # 3. 汇总PID输出位移
            d_deplacement = Vec3(0,0,0)
            d_deplacement.x = Kp * error.x + Ki * integral.x + Kd * derivative.x
            d_deplacement.y = Kp * error.y + Ki * integral.y + Kd * derivative.y
            d_deplacement.z = Kp * error.z + Ki * integral.z + Kd * derivative.z

            # 4. 移动限幅
            d_deplacement = limit_vec(d_deplacement, output_limit)

            # 5. 执行移动指令
            await player.move_to(
                player_x + d_deplacement.x, 
                player_y + d_deplacement.y, 
                player_z + d_deplacement.z, 
                speed=0.25
            )

            # 累积轨迹点
            trajectory.append((player_x, player_y, player_z))
            if len(trajectory) > max_trajectory_points:
                trajectory.pop(0)  # 移除最旧的点，保持长度

            # 绘制完整轨迹
            if len(trajectory) >= 2:
                await overworld.draw_path(
                    trajectory,      # 传递历史轨迹
                    color=0x00FF00,  # 绿色
                    duration=200     # 持续10秒
                )

            # 6. 为下一帧保存当前误差
            prev_error = Vec3(error.x, error.y, error.z)
            
            # 等待一个 Tick
            await asyncio.sleep(dt) 

    finally:
        await mc.close()

asyncio.run(main())