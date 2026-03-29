import asyncio
from pycraft import PyModClient

class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self):
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    def normalize(self):
        l = self.length()
        if l == 0:
            return Vec3(0, 0, 0)
        return Vec3(self.x / l, self.y / l, self.z / l)

    def tuple(self):
        return (self.x, self.y, self.z)

    def __repr__(self):
        return f"Vec3({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

def clamp(v, limit):
    if v > limit: return limit
    if v < -limit: return -limit
    return v

def limit_vec(v, max_len) -> Vec3:
    length = v.length()
    if length > max_len:
        s = max_len / length
        return v * s
    return v

async def main():
    mc = PyModClient()
    await mc.connect()
    try:
        overworld = mc.overworld()
        players = await overworld.get_players()
        player = players[0]
        await player.set_perspective(1)
        p_x, p_y, p_z = await player.get_pos()
        
        # 生成小猪实体
        pig = await overworld.spawn_entity(
            "minecraft:pig",
            p_x, p_y, p_z
        )

        # PID参数
        Kp = 0.2
        Ki = 0.05
        Kd = 0.1

        integral = Vec3(0,0,0)
        prev_error = Vec3(0,0,0)
        derivative = Vec3(0,0,0)

        dt = 0.05
        integral_limit = 5
        output_limit = 0.3

        # 持续追逐
        while True:
            # 获取小猪位置
            pig_x, pig_y, pig_z = await pig.get_pos()
            # 获取玩家位置
            player_x, player_y, player_z = await player.get_pos()
            error = Vec3(pig_x - player_x, pig_y - player_y, pig_z - player_z)

            # I
            integral.x += error.x * dt
            integral.y += error.y * dt
            integral.z += error.z * dt
            integral.x = clamp(integral.x, integral_limit)
            integral.y = clamp(integral.y, integral_limit)
            integral.z = clamp(integral.z, integral_limit)

            # D
            derivative.x = (error.x - prev_error.x) / dt
            derivative.y = (error.y - prev_error.y) / dt
            derivative.z = (error.z - prev_error.z) / dt

            # PID
            d_deplacement = Vec3(0,0,0)
            d_deplacement.x = Kp * error.x + Ki * integral.x + Kd * derivative.x
            d_deplacement.y = Kp * error.y + Ki * integral.y + Kd * derivative.y
            d_deplacement.z = Kp * error.z + Ki * integral.z + Kd * derivative.z

            # 限幅
            d_deplacement = limit_vec(d_deplacement, output_limit)

            # 玩家移动
            await player.move_to(player_x + d_deplacement.x, player_y + d_deplacement.y, player_z + d_deplacement.z, speed=0.25)
            # 画轨迹(目前这两种效果都不好)
            # await overworld.draw_path([(player_x, player_y, player_z), (player_x + d_deplacement.x, player_y + d_deplacement.y, player_z + d_deplacement.z)], color=0xFF0000, duration=40)
            await overworld.spawn_particle(player_x + d_deplacement.x, player_y + d_deplacement.y + 3, player_z + d_deplacement.z, count = 20)
            prev_error = Vec3(error.x, error.y, error.z)
            await asyncio.sleep(dt) 

    finally:
        await mc.close()

asyncio.run(main())