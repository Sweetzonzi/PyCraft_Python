import asyncio
import random
import math
from typing import List, Tuple, Dict, Optional
from pycraft import PyModClient, Entity


class Field:
    """田地类，代表一块种植区域"""

    CROP_TYPES = {
        0: ("minecraft:potatoes", "马铃薯", "green"),
        1: ("minecraft:carrots", "胡萝卜", "orange"),
        2: ("minecraft:wheat", "小麦", "yellow")
    }

    def __init__(self, field_id: int, center_pos: Tuple[int, int, int]):
        """
        初始化田地

        Args:
            field_id: 田地ID (0:马铃薯, 1:胡萝卜, 2:小麦)
            center_pos: 田地中心坐标 (x, y, z)
        """
        self.id = field_id
        crop_info = self.CROP_TYPES[field_id]
        self.crop_block = crop_info[0]  # 方块ID
        self.crop_name = crop_info[1]   # 作物名称
        self.color = crop_info[2]       # 颜色标识
        self.center_pos = center_pos

        # 田地参数
        self.base_value = 1.0  # 基础价值，所有田地相同（初始价格=1）
        self.current_price = 1.0  # 当前实际价格（缓慢调整）
        self.target_price = 1.0   # 目标价格
        self.entity_count = 0  # 当前实体数量
        self.current_gold_height = 1  # 当前金块高度（可视化）
        self.current_diamond_height = 0  # 当前钻石块高度（可视化，每10个金块换1个钻石块）

        # 价格调整参数
        self.learning_rate = 0.1  # 学习率（0-1）
        self.price_step = 0.5     # 最小调整步长
        self.min_price = 0.5      # 最低价格
        self.max_price = 10.0     # 最高价格

        # 田地边界（用于可视化）
        self.size = 5  # 5x5的田地
        self.fence_height = 1  # 栅栏高度

    @property
    def price(self) -> float:
        """获取当前价格（兼容性属性）"""
        return self.current_price

    @price.setter
    def price(self, value: float) -> None:
        """设置当前价格（兼容性属性）"""
        self.current_price = value

    def calculate_price(self, alpha: float) -> float:
        """计算当前价格：价格 = 基础价值 + α × 实体数量（兼容性方法，计算目标价格）"""
        self.target_price = self.base_value + alpha * self.entity_count
        self.target_price = max(self.min_price, min(self.target_price, self.max_price))
        return self.target_price

    def calculate_target_price(self, alpha: float) -> float:
        """计算目标价格"""
        self.target_price = self.base_value + alpha * self.entity_count
        self.target_price = max(self.min_price, min(self.target_price, self.max_price))
        return self.target_price

    def adjust_price_toward_target(self) -> float:
        """缓慢调整当前价格向目标价格靠近"""
        if abs(self.current_price - self.target_price) < self.price_step:
            self.current_price = self.target_price
        else:
            adjustment = self.learning_rate * (self.target_price - self.current_price)
            if abs(adjustment) > self.price_step:
                adjustment = self.price_step * (1 if adjustment > 0 else -1)
            self.current_price += adjustment
            self.current_price = max(self.min_price, min(self.current_price, self.max_price))
        return self.current_price

    def get_boundary_coords(self) -> Tuple[int, int, int, int, int, int]:
        """获取田地的边界坐标"""
        x, y, z = self.center_pos
        half_size = self.size // 2
        return (
            x - half_size, y, z - half_size,
            x + half_size, y, z + half_size
        )

    def get_gold_position(self) -> Tuple[int, int, int]:
        """获取金块位置（栅栏外侧）"""
        x, y, z = self.center_pos
        # 金块放在田地前方（Z+方向）外侧
        return (x, y + 1, z + self.size // 2 + 2)

    def get_diamond_position(self) -> Tuple[int, int, int]:
        """获取钻石块位置（金块旁边，X方向偏移）"""
        x, y, z = self.center_pos
        # 钻石块放在金块右侧（X+方向）
        return (x + 2, y + 1, z + self.size // 2 + 2)

    def get_entity_gathering_area(self) -> Tuple[int, int, int]:
        """获取实体聚集区域（田地前方的空地）"""
        x, y, z = self.center_pos
        return (x, y + 1, z + self.size // 2 + 5)


class AuctionEntity:
    """拍卖实体类，代表一个参与拍卖的村民"""

    def __init__(self, entity_id: int, initial_pos: Tuple[int, int, int]):
        """
        初始化实体

        Args:
            entity_id: 实体ID
            initial_pos: 初始位置
        """
        self.id = entity_id
        self.name = f"村民_{entity_id:02d}"
        self.position = initial_pos
        self.target_field_id: Optional[int] = None
        self.preferences: List[float] = []  # 对每块田地的偏好值
        self.entity_obj = None  # 实际的Pycraft实体对象（玩家）

    def generate_preferences(self, num_fields: int) -> None:
        """生成随机偏好（0-100之间的随机整数）"""
        self.preferences = [random.randint(0, 100) for _ in range(num_fields)]

    def calculate_utilities(self, fields: List[Field]) -> List[float]:
        """计算对每块田地的效用：效用 = 偏好 - 价格"""
        return [self.preferences[i] - fields[i].price for i in range(len(fields))]

    def choose_field(self, fields: List[Field]) -> int:
        """选择效用最高的田地，返回田地ID"""
        utilities = self.calculate_utilities(fields)
        best_field_id = max(range(len(utilities)), key=lambda i: utilities[i])

        # 如果所有效用都为负，可以选择不参与（返回-1）
        if utilities[best_field_id] < 0:
            return -1

        self.target_field_id = best_field_id
        return best_field_id


class AuctionSimulator:
    """拍卖模拟器主类"""

    def __init__(self, host='localhost', port=8086):
        self.client = PyModClient(host, port)
        self.level = None

        # 模拟参数
        self.num_fields = 3
        self.num_entities = 3  # 村民数量改为3个
        self.alpha = 3.0  # 价格敏感系数
        self.epsilon = 0.1  # 出价增量常数
        self.max_iterations = 50  # 最大迭代次数
        self.stability_window = 5  # 稳定性检测窗口（需要连续5轮无变化）
        self.oscillation_window = 5  # 震荡检测窗口

        # 数据存储
        self.fields: List[Field] = []
        self.entities: List[AuctionEntity] = []  # 参与拍卖的村民
        self.players: List = []  # 观察者玩家（不参与拍卖）
        self.history: List[Dict] = []  # 记录历史数据
        self.decision_history: List[Dict[int, int]] = []  # 记录决策历史，用于检测震荡

        # 田地布局参数
        self.field_spacing = 20  # 田地间距
        self.base_y = 64  # 基础Y坐标

        # 延迟控制
        self.delay_between_steps = 2.0  # 默认2秒延迟

    async def initialize(self):
        """初始化连接和世界"""
        print("正在连接Pycraft服务器...")
        await self.client.connect()
        self.level = self.client.overworld()
        print("连接成功！")

        # 清理区域（可选）
        await self.clear_area()

        # 创建田地
        await self.create_fields()

        # 创建实体
        await self.create_entities()

        # 初始化价格
        self.update_prices()

        # 显示初始状态
        await self.visualize_state()

    async def clear_area(self):
        """清理区域（创建一块平地）"""
        print("正在清理区域...")
        # 清理一个较大的区域
        x1, z1 = -50, -30
        x2, z2 = 50, 30
        y = self.base_y - 1

        # 创建草地方块
        await self.level.set_blocks(x1, y, z1, x2, y, z2, "minecraft:grass_block")
        # 清理上方的方块
        await self.level.set_blocks(x1, y+1, z1, x2, y+10, z2, "minecraft:air")
        print("区域清理完成")

    async def clear_existing_villagers(self):
        """清理现有的村民实体（避免村民数量过多）"""
        print("正在清理现有村民...")
        try:
            # 尝试获取区域内的所有实体
            # 注意：Pycraft API可能没有直接获取实体的方法，这里尝试使用命令
            clear_x1, clear_z1 = -50, -30
            clear_x2, clear_z2 = 50, 30
            clear_y1 = self.base_y - 10
            clear_y2 = self.base_y + 10

            # 尝试执行命令清理村民
            command = f"/kill @e[type=minecraft:villager,x={clear_x1},y={clear_y1},z={clear_z1},dx={clear_x2-clear_x1},dy={clear_y2-clear_y1},dz={clear_z2-clear_z1}]"
            resp = await self.client.request("execute_command", {
                "level": self.level.name,
                "command": command
            })
            if resp.get("success"):
                print("已清理区域内的村民")
            else:
                print("清理村民命令执行失败（可能没有村民或命令不被支持）")
        except Exception as e:
            print(f"清理村民时出错（可能API不支持）: {e}")
            # 如果无法清理，只打印警告
            print("警告：无法清理现有村民，可能会有多余的村民")

    async def create_fields(self):
        """创建三块田地"""
        print("正在创建田地...")

        # 田地中心X坐标（等距排列）
        start_x = -self.field_spacing
        base_z = 0

        for i in range(self.num_fields):
            center_x = start_x + i * self.field_spacing
            center_pos = (center_x, self.base_y, base_z)

            field = Field(i, center_pos)
            self.fields.append(field)

            # 创建田地可视化
            await self.create_field_visualization(field)

            print(f"  创建田地 {i}: {field.crop_name} 在位置 {center_pos}")

    async def create_field_visualization(self, field: Field):
        """创建田地的可视化元素"""
        x, y, z = field.center_pos
        size = field.size
        half_size = size // 2

        # 1. 创建耕地
        for dx in range(-half_size, half_size + 1):
            for dz in range(-half_size, half_size + 1):
                await self.level.set_block(x + dx, y, z + dz, "minecraft:farmland")


        # 2. 创建栅栏
        fence_y = y + 1
        for dx in range(-half_size - 1, half_size + 2):
            # 前后栅栏
            await self.level.set_block(x + dx, fence_y, z - half_size - 1, "minecraft:oak_fence")
            await self.level.set_block(x + dx, fence_y, z + half_size + 1, "minecraft:oak_fence")

        for dz in range(-half_size - 1, half_size + 2):
            # 左右栅栏
            await self.level.set_block(x - half_size - 1, fence_y, z + dz, "minecraft:oak_fence")
            await self.level.set_block(x + half_size + 1, fence_y, z + dz, "minecraft:oak_fence")

        # 3. 种植作物（使用成熟的作物）
        crop_block = field.crop_block
        for dx in range(-half_size, half_size + 1):
            for dz in range(-half_size, half_size + 1):
                # 放置作物
                await self.level.set_block(x + dx, y + 1, z + dz, crop_block)

                # 对于某些作物，可以添加装饰
                if field.id == 0:  # 马铃薯
                    # 可以添加一些装饰方块
                    pass
                elif field.id == 1:  # 胡萝卜
                    pass
                elif field.id == 2:  # 小麦
                    pass

        # 4. 放置金块和钻石块（十进制进位系统）
        gold_x, gold_y, gold_z = field.get_gold_position()
        diamond_x, diamond_y, diamond_z = field.get_diamond_position()

        # 初始价格=1，所以1个金块，0个钻石块
        await self.level.set_block(gold_x, gold_y, gold_z, "minecraft:gold_block")

        # 确保钻石块位置是空的（初始价格为1，没有钻石块）
        await self.level.set_block(diamond_x, diamond_y, diamond_z, "minecraft:air")

        # 如果有更高的位置（之前运行残留的），也清理一下
        for h in range(1, 10):
            await self.level.set_block(gold_x, gold_y + h, gold_z, "minecraft:air")
            await self.level.set_block(diamond_x, diamond_y + h, diamond_z, "minecraft:air")

        # 5. 放置信息牌
        sign_x, sign_y, sign_z = x, y + 2, z - half_size - 2
        # 注意：Minecraft中放置告示牌需要特殊处理，这里先跳过

    async def spawn_villager(self, x: float, y: float, z: float) -> Optional[Entity]:
        """
        生成一个村民实体
        返回Entity对象，如果失败则返回None
        """
        # 尝试多种可能的请求类型
        request_types = [
            ("spawn_entity", {"level": self.level.name, "entity_type": "minecraft:villager", "x": x, "y": y, "z": z}),
            ("summon_entity", {"level": self.level.name, "entity_type": "minecraft:villager", "x": x, "y": y, "z": z}),
            ("create_entity", {"level": self.level.name, "entity_type": "minecraft:villager", "x": x, "y": y, "z": z}),
            ("get_entity", {"level": self.level.name, "entity_type": "minecraft:villager", "x": x, "y": y, "z": z}),
        ]

        for req_type, data in request_types:
            try:
                resp = await self.client.request(req_type, data)
                print(f"尝试 {req_type}: 成功={resp.get('success')}")
                if resp.get("success"):
                    data = resp["data"]
                    # 尝试不同的ID字段名
                    entity_id = data.get("entity_id") or data.get("id") or data.get("entity")
                    if entity_id is not None:
                        entity_name = data.get("name", f"villager_{entity_id}")
                        entity = Entity(self.client, self.level, entity_id, entity_name)
                        print(f"生成村民 {entity_name} 在 ({x}, {y}, {z}) 通过 {req_type}")
                        return entity
                    else:
                        print(f"{req_type} 响应中没有实体ID: {data}")
                else:
                    print(f"{req_type} 失败: {resp.get('error_message')}")
            except Exception as e:
                print(f"{req_type} 出错: {e}")
                continue

        # 如果所有请求都失败，尝试使用命令
        try:
            # 尝试执行 /summon 命令
            command = f"/summon minecraft:villager {x} {y} {z}"
            resp = await self.client.request("execute_command", {
                "level": self.level.name,
                "command": command
            })
            if resp.get("success"):
                # 命令执行成功，但可能不会返回实体ID
                # 我们可以尝试获取附近的实体
                print(f"命令执行成功: {command}")
                # 返回None，因为我们没有实体引用
                return None
        except Exception as e:
            print(f"执行命令失败: {e}")

        return None

    async def create_entities(self):
        """创建拍卖参与者和观察者"""
        print("正在创建拍卖参与者...")

        # 清理现有村民，避免村民数量过多
        await self.clear_existing_villagers()

        # 首先获取现有玩家作为观察者
        try:
            players = await self.level.get_players()
            self.players = players
            print(f"找到 {len(players)} 个观察者玩家")

            # 将玩家传送到观察位置（田地后方的高处）
            observer_x = 0  # 中间位置
            observer_y = self.base_y + 10  # 高处
            observer_z = -20  # 田地后方

            for i, player in enumerate(players):
                try:
                    await player.teleport(observer_x, observer_y, observer_z)
                    print(f"  玩家 {player.name} 传送到观察位置 ({observer_x}, {observer_y}, {observer_z})")
                except Exception as e:
                    print(f"  玩家 {player.name} 传送失败: {e}")
        except Exception as e:
            print(f"获取玩家失败，继续创建虚拟村民: {e}")
            self.players = []

        # 创建村民等待区（与田地等高的平台）
        print("正在创建村民等待区...")
        wait_area_y = self.base_y  # 与田地等高
        wait_area_z_start = 8  # 田地前方
        wait_area_z_end = 12
        wait_area_x_start = -30
        wait_area_x_end = 30

        # 创建石头平台
        await self.level.set_blocks(
            wait_area_x_start, wait_area_y, wait_area_z_start,
            wait_area_x_end, wait_area_y, wait_area_z_end,
            "minecraft:stone"
        )
        print(f"等待区平台创建在 Y={wait_area_y}, X=[{wait_area_x_start}, {wait_area_x_end}], Z=[{wait_area_z_start}, {wait_area_z_end}]")

        # 生成真实村民
        print(f"尝试生成 {self.num_entities} 个真实村民...")
        entities_created = 0

        # 计算村民在等待区内的均匀分布位置
        for i in range(self.num_entities):
            # 在等待区内均匀分布
            ratio = (i + 0.5) / self.num_entities  # 0到1之间
            x = wait_area_x_start + (wait_area_x_end - wait_area_x_start) * ratio
            z = wait_area_z_start + (wait_area_z_end - wait_area_z_start) * 0.5  # 居中在Z方向
            y = wait_area_y + 0.5  # 平台上方0.5格

            # 生成村民
            villager_entity = await self.spawn_villager(x, y, z)

            # 创建拍卖实体对象
            entity = AuctionEntity(i, (x, y, z))
            entity.name = f"村民_{i:02d}"
            entity.entity_obj = villager_entity  # 关联真实实体

            entity.generate_preferences(self.num_fields)
            self.entities.append(entity)

            if villager_entity:
                entities_created += 1
                print(f"  创建真实村民 {i}: {entity.name} 在 ({x:.1f}, {y:.1f}, {z:.1f})，偏好: {[round(p, 1) for p in entity.preferences]}")
            else:
                print(f"  创建虚拟村民 {i}: {entity.name}（真实实体生成失败），偏好: {[round(p, 1) for p in entity.preferences]}")

        print(f"村民生成完成: {entities_created} 个真实村民, {self.num_entities - entities_created} 个虚拟村民")

    def update_prices(self):
        """更新所有田地的价格（使用缓慢调整）"""
        for field in self.fields:
            field.calculate_target_price(self.alpha)
            field.adjust_price_toward_target()

    def configure_price_adjustment(self, learning_rate=0.1, price_step=0.5,
                                   min_price=0.5, max_price=10.0, delay=2.0):
        """配置价格调整参数"""
        self.delay_between_steps = delay

        for field in self.fields:
            field.learning_rate = learning_rate
            field.price_step = price_step
            field.min_price = min_price
            field.max_price = max_price

    async def visualize_state(self):
        """可视化当前状态（更新金块和钻石块高度，十进制进位系统）"""
        print("\n=== 当前状态 ===")

        for field in self.fields:
            # 计算期望的金块总数（价格四舍五入到最接近的整数）
            total_gold_blocks = max(1, int(round(field.current_price)))  # 至少1个金块

            # 十进制进位：每10个金块换1个钻石块
            desired_diamond_height = total_gold_blocks // 10  # 钻石块数量（十位）
            desired_gold_height = total_gold_blocks % 10      # 金块数量（个位），0-9

            # 如果金块数量为0且钻石块数量>0，则显示9个金块？不，应该是0个金块
            # 但为了可视化，当钻石块>0时，金块数量可以是0-9

            current_gold_height = field.current_gold_height
            current_diamond_height = field.current_diamond_height

            # 获取金块和钻石块位置
            gold_x, gold_y, gold_z = field.get_gold_position()
            diamond_x, diamond_y, diamond_z = field.get_diamond_position()

            # 逐步调整金块高度（每次最多变化2个金块，避免跳跃）
            max_change = 2  # 每轮最大金块变化数

            # 调整金块高度
            if desired_gold_height > current_gold_height:
                # 需要增加金块
                change = min(desired_gold_height - current_gold_height, max_change)
                for h in range(current_gold_height, current_gold_height + change):
                    await self.level.set_block(gold_x, gold_y + h, gold_z, "minecraft:gold_block")
                field.current_gold_height += change
            elif desired_gold_height < current_gold_height:
                # 需要减少金块
                change = min(current_gold_height - desired_gold_height, max_change)
                for h in range(current_gold_height - change, current_gold_height):
                    await self.level.set_block(gold_x, gold_y + h, gold_z, "minecraft:air")
                field.current_gold_height -= change
            # 如果高度不变，不做任何操作

            # 调整钻石块高度（每次最多变化1个钻石块）
            diamond_max_change = 1
            if desired_diamond_height > current_diamond_height:
                # 需要增加钻石块
                change = min(desired_diamond_height - current_diamond_height, diamond_max_change)
                for h in range(current_diamond_height, current_diamond_height + change):
                    await self.level.set_block(diamond_x, diamond_y + h, diamond_z, "minecraft:diamond_block")
                field.current_diamond_height += change
            elif desired_diamond_height < current_diamond_height:
                # 需要减少钻石块
                change = min(current_diamond_height - desired_diamond_height, diamond_max_change)
                for h in range(current_diamond_height - change, current_diamond_height):
                    await self.level.set_block(diamond_x, diamond_y + h, diamond_z, "minecraft:air")
                field.current_diamond_height -= change

            # 特殊处理：当金块从9增加到10时（进位），应该将9个金块换成1个钻石块
            # 但上面的逻辑已经处理了：金块数量会减少到0，钻石块会增加1

            print(f"田地 {field.crop_name}: 价格={field.current_price:.2f}, 目标价格={field.target_price:.2f}, 实体数={field.entity_count}, 金块={field.current_gold_height}, 钻石块={field.current_diamond_height}")

        # 显示村民选择
        for entity in self.entities:
            target_name = "无" if entity.target_field_id is None else self.fields[entity.target_field_id].crop_name
            print(f"{entity.name}: 目标={target_name}")

    async def run_simulation(self):
        """运行拍卖模拟（基于拍卖算法）"""
        print("\n=== 开始拍卖模拟 ===")
        print(f"参数: ε={self.epsilon}, 实体数={self.num_entities}, 田地数={self.num_fields}")

        # 初始化：所有田地价格从1.0开始，无持有者
        field_owners = {field.id: None for field in self.fields}  # 田地ID -> 实体ID
        # 初始化实体目标田地
        for entity in self.entities:
            entity.target_field_id = None

        # 显示初始状态
        print("\n--- 初始状态 ---")
        print("所有田地起价: 1.0")
        for field in self.fields:
            print(f"  {field.crop_name}: 价格={field.price:.2f}, 持有者=无")

        iteration = 0
        stabilized = False
        self.decision_history = []  # 清空决策历史

        while iteration < self.max_iterations and not stabilized:
            iteration += 1
            print(f"\n--- 第 {iteration} 轮 ---")

            changed_count = 0  # 记录本轮发生变化的实体数

            # 逐个实体进行拍卖决策（按顺序）
            for entity in self.entities:
                # 计算每个田地的效用（偏好 - 价格）
                utilities = []
                for field in self.fields:
                    utility = entity.preferences[field.id] - field.price
                    utilities.append(utility)

                # 找到效用最高的两个田地
                sorted_indices = sorted(range(len(utilities)), key=lambda i: utilities[i], reverse=True)
                best_idx = sorted_indices[0]
                second_best_idx = sorted_indices[1] if len(sorted_indices) > 1 else best_idx

                best_utility = utilities[best_idx]
                second_best_utility = utilities[second_best_idx]

                current_field_id = entity.target_field_id
                best_field_id = best_idx

                # 如果最佳效用为负，实体应弃权（放弃当前田地）
                if best_utility < 0:
                    if current_field_id is not None:
                        # 放弃当前持有的田地
                        field_owners[current_field_id] = None
                        entity.target_field_id = None
                        print(f"{entity.name}: 弃权（所有效用为负），放弃{self.fields[current_field_id].crop_name}")
                        changed_count += 1
                    # 如果未持有任何田地，则无需行动
                    continue

                # 计算出价增量
                bid_increment = (best_utility - second_best_utility) + self.epsilon
                if bid_increment < 0:
                    bid_increment = self.epsilon  # 保证至少为epsilon

                # 如果当前持有的就是最佳田地，且效用已经最高，则不需要行动
                if current_field_id == best_field_id:
                    # 检查是否需要调整价格（如果当前持有但价格不是最优）
                    continue

                # 否则，尝试获得最佳田地
                target_field = self.fields[best_field_id]
                old_owner_id = field_owners[best_field_id]

                # 出价：提高价格
                old_price = target_field.price
                target_field.price = old_price + bid_increment
                print(f"{entity.name}: 出价{bid_increment:.2f}获得{target_field.crop_name}, 价格{old_price:.2f}→{target_field.price:.2f}")

                # 如果该田地已有持有者，释放该持有者
                if old_owner_id is not None:
                    old_owner = self.entities[old_owner_id]
                    old_owner.target_field_id = None
                    print(f"  → 释放原持有者 {old_owner.name}")

                # 更新持有关系
                field_owners[best_field_id] = entity.id
                entity.target_field_id = best_field_id

                # 如果实体原先持有其他田地，释放该田地
                if current_field_id is not None and current_field_id != best_field_id:
                    field_owners[current_field_id] = None
                    # 注意：该田地可能被其他实体持有，但当前实体是持有者，所以直接释放

                changed_count += 1

            # 更新田地实体数量（用于可视化）
            for field in self.fields:
                field.entity_count = 1 if field_owners[field.id] is not None else 0

            # 记录当前决策
            current_decisions = {entity.id: (entity.target_field_id if entity.target_field_id is not None else -1) for entity in self.entities}
            self.decision_history.append(current_decisions.copy())

            # 可视化更新
            await self.visualize_state()

            # 显示本轮结果
            print(f"\n第 {iteration} 轮结果:")
            for field in self.fields:
                owner_id = field_owners[field.id]
                owner_name = "无" if owner_id is None else self.entities[owner_id].name
                print(f"  {field.crop_name}: 价格={field.price:.2f}, 持有者={owner_name}")

            print(f"  本轮变化: {changed_count}/{len(self.entities)} 个实体改变了选择")

            # 移动实体到目标田地
            await self.move_entities(current_decisions)

            # 只保留最近足够轮数的历史记录
            if len(self.decision_history) > max(self.stability_window, self.oscillation_window):
                self.decision_history.pop(0)

            # 检查稳定性（连续5轮无变化）
            if iteration >= self.stability_window:
                stabilized = self.check_stability()
                if stabilized:
                    print(f"\n系统在第 {iteration} 轮达到稳定状态（连续{self.stability_window}轮无变化）！")
                    break

            # 记录历史数据
            self.record_history(iteration)

            # 等待一段时间
            if self.delay_between_steps > 0:
                print(f"等待 {self.delay_between_steps} 秒...")
                await asyncio.sleep(self.delay_between_steps)

        if not stabilized and iteration >= self.max_iterations:
            print(f"\n模拟在 {self.max_iterations} 轮后未达到稳定状态")

        # 显示最终结果
        await self.show_final_results(stabilized, oscillating=False)

    async def move_entities(self, decisions: Dict[int, int]):
        """移动实体到目标田地"""
        for entity_id, field_id in decisions.items():
            if field_id >= 0:  # 有效的选择
                entity = self.entities[entity_id]
                field = self.fields[field_id]

                target_pos = field.get_entity_gathering_area()
                print(f"{entity.name} 移动到 {field.crop_name} 附近 {target_pos}")

                # 更新实体位置
                entity.position = target_pos

                # 如果有关联的实际实体对象，则进行移动
                if entity.entity_obj:
                    try:
                        # 使用瞬移或移动
                        await entity.entity_obj.teleport(*target_pos)
                        # 或者使用平滑移动：await entity.entity_obj.move_to(*target_pos, speed=0.2)
                        print(f"  → 实际移动了 {entity.name}")
                    except Exception as e:
                        print(f"  → 移动失败: {e}")
                else:
                    print(f"  → 虚拟实体，未实际移动")

    def check_stability(self) -> bool:
        """检查系统是否稳定（连续5轮无变化）"""
        if len(self.decision_history) < self.stability_window:
            return False

        # 检查最近stability_window轮决策是否完全相同
        recent_history = self.decision_history[-self.stability_window:]

        # 比较每一轮是否都相同
        first_decision = recent_history[0]
        for decision in recent_history[1:]:
            if decision != first_decision:
                # 计算当前轮和上一轮的变化情况（用于显示）
                current = self.decision_history[-1]
                previous = self.decision_history[-2] if len(self.decision_history) >= 2 else {}
                if previous:
                    changed = sum(1 for eid in current if current[eid] != previous.get(eid))
                    print(f"稳定性检测: {changed}/{len(current)} 个实体改变了选择")
                return False

        print(f"稳定性检测: 连续{self.stability_window}轮决策完全相同，系统已稳定")
        return True

    def check_oscillation(self) -> bool:
        """检查系统是否出现震荡（循环模式）"""
        if len(self.decision_history) < self.oscillation_window:
            return False

        recent_history = self.decision_history[-self.oscillation_window:]

        # 检查是否有长度为2的循环模式（A,B,A,B,...）
        if self.oscillation_window >= 4:
            # 检查ABAB模式
            pattern1 = recent_history[0]
            pattern2 = recent_history[1]
            is_abab = True
            for i in range(0, len(recent_history), 2):
                if i < len(recent_history) and recent_history[i] != pattern1:
                    is_abab = False
                    break
                if i+1 < len(recent_history) and recent_history[i+1] != pattern2:
                    is_abab = False
                    break
            if is_abab:
                print(f"震荡检测: 发现ABAB循环模式（长度2）")
                return True

        # 检查是否有长度为3的循环模式（A,B,C,A,B,C,...）
        if self.oscillation_window >= 6:
            pattern1 = recent_history[0]
            pattern2 = recent_history[1]
            pattern3 = recent_history[2]
            is_abcabc = True
            for i in range(0, len(recent_history), 3):
                if i < len(recent_history) and recent_history[i] != pattern1:
                    is_abcabc = False
                    break
                if i+1 < len(recent_history) and recent_history[i+1] != pattern2:
                    is_abcabc = False
                    break
                if i+2 < len(recent_history) and recent_history[i+2] != pattern3:
                    is_abcabc = False
                    break
            if is_abcabc:
                print(f"震荡检测: 发现ABCABC循环模式（长度3）")
                return True

        # 检查是否有任何重复的模式（更通用的检测）
        # 将决策转换为可哈希的元组形式
        decision_tuples = []
        for decision in recent_history:
            # 将决策字典转换为排序后的元组
            decision_tuple = tuple(sorted(decision.items()))
            decision_tuples.append(decision_tuple)

        # 检查是否有重复的决策状态
        if len(set(decision_tuples)) < len(decision_tuples):
            print(f"震荡检测: 发现重复决策状态")
            return True

        return False

    def record_history(self, iteration: int):
        """记录历史数据"""
        snapshot = {
            "iteration": iteration,
            "prices": [field.price for field in self.fields],
            "entity_counts": [field.entity_count for field in self.fields],
            "field_names": [field.crop_name for field in self.fields]
        }
        self.history.append(snapshot)

    async def show_final_results(self, stabilized: bool = False, oscillating: bool = False):
        """显示最终拍卖结果"""
        print("\n" + "="*60)
        print("拍卖最终结果")
        print("="*60)

        # 显示拍卖结果状态
        if stabilized:
            print("拍卖结果: 稳定收敛")
        elif oscillating:
            print("拍卖结果: 结果为震荡")
        else:
            print("拍卖结果: 未收敛")

        print(f"总轮数: {len(self.history)}")
        print(f"参数: α={self.alpha}, 村民数={self.num_entities}")

        # 显示田地最终状态
        print("\n" + "-"*40)
        print("田地拍卖结果")
        print("-"*40)

        for field in self.fields:
            print(f"\n{field.crop_name} 田地:")
            print(f"\n最终价格: {field.price:.2f} 单位（1单位=1金块，10金块=1钻石块）")
            print(f"\n获得村民: {field.entity_count} 人")
            print(f"\n基础价值: {field.base_value}")
            print(f"\n价格涨幅: {field.price - field.base_value:+.2f}")

            # 显示获得该田地的村民名单
            winners = []
            for entity in self.entities:
                if entity.target_field_id == field.id:
                    winners.append(entity.name)

            if winners:
                print(f"获得村民: {', '.join(winners)}")
            else:
                print(f"获得村民: 无")

        # 显示村民拍卖结果
        print("\n" + "-"*40)
        print("村民拍卖结果")
        print("-"*40)

        for entity in self.entities:
            if entity.target_field_id is not None and entity.target_field_id >= 0:
                field = self.fields[entity.target_field_id]
                utility = entity.preferences[field.id] - field.price
                print(f"{entity.name}:")
                print(f"\n获得田地: {field.crop_name}")
                print(f"\n支付价格: {field.price:.2f}")
                print(f"\n偏好价值: {entity.preferences[field.id]:.1f}")
                print(f"\n净效用: {utility:+.2f}")
            else:
                print(f"{entity.name}: 弃权（未获得任何田地）")

        # 显示弃权统计
        abstain_count = sum(1 for entity in self.entities
                          if entity.target_field_id is None or entity.target_field_id < 0)
        if abstain_count > 0:
            print(f"\n弃权村民: {abstain_count} 人")
            abstain_names = [entity.name for entity in self.entities
                           if entity.target_field_id is None or entity.target_field_id < 0]
            print(f"弃权名单: {', '.join(abstain_names)}")

        # 显示价格变化趋势
        if len(self.history) > 1:
            print("\n" + "-"*40)
            print("价格变化趋势")
            print("-"*40)

            for i, field in enumerate(self.fields):
                start_price = self.history[0]["prices"][i]
                end_price = self.history[-1]["prices"][i]
                change = end_price - start_price
                change_percent = (change / start_price * 100) if start_price > 0 else 0
                print(f"{field.crop_name}: {start_price:.2f} → {end_price:.2f} ({change:+.2f}, {change_percent:+.1f}%)")

        # 显示观察者信息
        if self.players:
            print("\n" + "-"*40)
            print("观察者信息")
            print("-"*40)
            print(f"观察者玩家: {len(self.players)} 人")
            for i, player in enumerate(self.players):
                print(f"  玩家 {i+1}: {player.name}")

        print("\n" + "="*60)
        print("拍卖结束")
        print("="*60)

    async def interactive_parameter_adjustment(self):
        """交互式参数调整"""
        print("\n=== 参数调整 ===")

        while True:
            print(f"\n当前参数: α={self.alpha}")
            print("选项:")
            print("  1. 调整α值")
            print("  2. 运行模拟")
            print("  3. 重新开始")
            print("  4. 退出")

            try:
                choice = input("请选择 (1-4): ").strip()

                if choice == "1":
                    new_alpha = float(input("请输入新的α值 (推荐 0.5-3.0): "))
                    if 0.1 <= new_alpha <= 10:
                        self.alpha = new_alpha
                        print(f"α值已更新为 {self.alpha}")
                    else:
                        print("α值应在0.1到10之间")

                elif choice == "2":
                    await self.run_simulation()
                    break

                elif choice == "3":
                    print("重新开始模拟...")
                    await self.initialize()
                    await self.run_simulation()
                    break

                elif choice == "4":
                    print("退出程序")
                    break

                else:
                    print("无效选择")

            except ValueError:
                print("请输入有效的数字")
            except Exception as e:
                print(f"错误: {e}")

    async def close(self):
        """关闭连接"""
        await self.client.close()
        print("连接已关闭")


async def main():
    """主函数"""
    print("="*60)
    print("拍卖算法可视化 - Pycraft实现")
    print("="*60)

    simulator = AuctionSimulator()

    try:
        # 初始化
        await simulator.initialize()

        # 交互式参数调整和运行
        await simulator.interactive_parameter_adjustment()

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await simulator.close()


if __name__ == "__main__":
    asyncio.run(main())