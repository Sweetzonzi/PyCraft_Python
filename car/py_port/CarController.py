from py_port import get_agent_manager
import time
import sys

class CarController:
    def __init__(self, car_id):
        self.car = get_agent_manager().get_agent(car_id)
        print(f"[CarController] Connected to car {car_id}")

    def forward(self, power=0.5):
        """前进"""
        self.car.drive(power, 0, False)

    def backward(self, power=0.5):
        """后退"""
        self.car.drive(-power, 0, False)

    def turn_left(self, amount=0.5):
        """左转"""
        self.car.drive(0, -amount, False)

    def turn_right(self, amount=0.5):
        """右转"""
        self.car.drive(0, amount, False)

    def brake(self):
        """刹车"""
        self.car.drive(0, 0, True)

    def handbrake(self):
        """手刹（急停）"""
        self.car.handbrake()
        time.sleep(0.1)
        self.car.release_handbrake()

    def drive_with_input(self, throttle, steering, brake=False):
        """直接设置控制值"""
        self.car.drive(throttle, steering, brake)

    def get_speed(self):
        """获取当前速度"""
        return self.car.get_speed()

    def set_position(self, x, y, z):
        """设置位置"""
        self.car.set_position(x, y, z)

    def get_position(self):
        """获取位置"""
        return self.car.get_position()


# 使用示例
if __name__ == "__main__":
    car_id = 1
    if len(sys.argv) > 1:
        car_id = int(sys.argv[1])

    print(f"[CarController] Controlling car {car_id}")
    car = CarController(car_id)

    # 前进2秒
    print("Forward...")
    car.forward(0.8)
    time.sleep(2)

    # 刹车
    print("Brake...")
    car.brake()
    time.sleep(0.5)

    # 左转并前进
    print("Turn left while forward...")
    car.forward(0.5)
    car.turn_left(0.6)
    time.sleep(1)

    # 停车
    print("Stop...")
    car.brake()

    print(f"Final speed: {car.get_speed():.2f}")