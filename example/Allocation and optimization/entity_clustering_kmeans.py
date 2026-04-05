import asyncio
import random
import sys
import os
import math
from typing import List, Tuple, Dict, Set

# 添加父目录到路径，以便导入pycraft模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pycraft import PyModClient

# 实体类型列表（三种友好实体：猪、牛、村民）
FRIENDLY_ENTITIES = [
    "minecraft:cow",
    "minecraft:pig",
    "minecraft:villager",
]


# 聚类中心可视化方块
CENTER_BLOCK = "minecraft:beacon"  
FENCE_BLOCK = "minecraft:oak_fence"    

# 配置参数
ENCLOSURE_SIZE = 120           
MIN_ENTITIES = 100          
MAX_ENTITIES = 110            
ENTITY_TYPES_COUNT = 3       
KMEANS_ITERATIONS = 5         
GATHER_AREA_SIZE = 15          
CLASSIFICATION_FENCE_SIZE = 15

async def create_enclosure(level, center_x: float, center_z: float, player_y: float, size: int = 150) -> None:
    
    try:
        half_size = size // 2
        x_min = int(center_x - half_size)
        x_max = int(center_x + half_size)
        z_min = int(center_z - half_size)
        z_max = int(center_z + half_size)
        y = int(player_y)  

        for corner_x in [x_min, x_max]:
            for corner_z in [z_min, z_max]:
                for dy in range(-2, 4):
                    await level.set_block(corner_x, y + dy, corner_z, "minecraft:air")
        await asyncio.sleep(0.5)
        fence_height = 2
        
        side_count = 0
        side_count += 1
       
        for z in range(z_min, z_max + 1):
            await level.set_blocks(x_min, y, z, x_min, y + fence_height, z, FENCE_BLOCK)
        side_count += 1
      
        for z in range(z_min, z_max + 1):
            await level.set_blocks(x_max, y, z, x_max, y + fence_height, z, FENCE_BLOCK)
        side_count += 1
       
        for x in range(x_min + 1, x_max):
            await level.set_blocks(x, y, z_min, x, y + fence_height, z_min, FENCE_BLOCK)
           
        side_count += 1
        for x in range(x_min + 1, x_max):
            await level.set_blocks(x, y, z_max, x, y + fence_height, z_max, FENCE_BLOCK)

    except Exception as e:
        print(f"建造围墙失败: {e}")
        import traceback
        traceback.print_exc()
        raise

async def spawn_entities_in_area(client, level, center_x: float, center_z: float, player_y: float,min_count: int = 50, max_count: int = 60, entity_types_count: int = 4) -> List[Tuple]:
    try:
        total_entities = random.randint(min_count, max_count)
        entity_types_count = 3
        selected_types = FRIENDLY_ENTITIES[:entity_types_count]  
        half_size = ENCLOSURE_SIZE // 2  
        x_min = center_x - half_size
        x_max = center_x + half_size
        z_min = center_z - half_size
        z_max = center_z + half_size
        entities = []
        for i in range(total_entities):
            entity_type = random.choice(selected_types)
            x = random.uniform(x_min + 2, x_max - 2)
            z = random.uniform(z_min + 2, z_max - 2)
            y = player_y
            await ensure_ground_support(level, x, y, z)
            print(f"生成实体 {i+1}/{total_entities}: {entity_type} 在 ({x:.1f}, {y:.1f}, {z:.1f})")
            try:
                entity = await level.spawn_entity(x, y, z, entity_type)
                if entity:
                    entities.append((entity, entity_type, x, y, z))
                else:
                    print(f"  实体生成失败，跳过")
            except Exception as e:
                print(f"  生成实体异常: {e}")
            await asyncio.sleep(0.1)  # 避免请求过快

        print(f"成功生成 {len(entities)} 个实体")
        return entities

    except Exception as e:
        print(f"生成实体失败: {e}")
        raise

async def spawn_entity_direct(client, level, x: float, y: float, z: float, entity_type: str):
    
    try:
        resp = await client.request(
            "spawn_entity",
            {
                "level": level.name,
                "x": x,
                "y": y,
                "z": z,
                "entity_type": entity_type
            }
        )
        if not resp.get("success"):
            print(f"生成实体失败: {resp.get('error_message', '未知错误')}")
            return None
        entity_id = resp.get("data", {}).get("id")
        if not entity_id:
            print(f"生成实体失败: 响应中没有实体ID")
            return None
        print(f"成功生成实体: {entity_type} (ID: {entity_id}) 在 ({x:.1f}, {y:.1f}, {z:.1f})")
        # 创建 Entity 对象
        from pycraft import Entity
        return Entity(client, level, entity_id, entity_type)
    except Exception as e:
        print(f"请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None

async def ensure_ground_support(level, x: float, target_y: float, z: float) -> bool:
   
    try:
        # 检查target_y-1位置是否有固体方块
        block_below = await level.get_block(int(x), int(target_y - 1), int(z))
        if block_below in ["minecraft:air", "minecraft:water", "minecraft:lava"]:
            # 放置一个临时支撑方块
            await level.set_block(int(x), int(target_y - 1), int(z), "minecraft:grass_block")
            print(f"  放置支撑方块在 ({int(x)}, {int(target_y-1)}, {int(z)})")
            return True
        return False
    except Exception as e:
        print(f"确保地面支撑失败: {e}")
        return False

async def init_cluster_centers(level, center_x: float, center_z: float, player_y: float,
                               entity_types: List[str], size: int = ENCLOSURE_SIZE) -> Dict[str, Tuple[float, float, float]]:
    
    try:
        if not entity_types:
            print("警告: 实体类型列表为空，无法初始化聚类中心")
            return {}

        half_size = size // 2
        x_min = center_x - half_size + 10  # 离边界至少10格
        x_max = center_x + half_size - 10
        z_min = center_z - half_size + 10
        z_max = center_z + half_size - 10

        centers = {}

        for entity_type in entity_types:
            # 随机位置
            x = random.uniform(x_min, x_max)
            z = random.uniform(z_min, z_max)
            y = player_y + 0.5  # 半格高度，放在地面上

            # 放置中心标记方块
            await level.set_block(int(x), int(y), int(z), CENTER_BLOCK)

            centers[entity_type] = (x, y, z)
            print(f"初始化聚类中心 '{entity_type}': ({x:.1f}, {y:.1f}, {z:.1f})")

        return centers

    except Exception as e:
        print(f"初始化聚类中心失败: {e}")
        raise

async def get_entities_current_positions(entities: List[Tuple]) -> List[Tuple]:
    updated_entities = []
    for entity_obj, entity_type, _, _, _ in entities:
        try:
            x, y, z = await entity_obj.get_pos()
            updated_entities.append((entity_obj, entity_type, x, y, z))
        except Exception as e:
            print(f"获取实体位置失败: {e}")
            # 保持原位置
            updated_entities.append((entity_obj, entity_type, 0, 0, 0))
    return updated_entities

async def update_cluster_centers(entities: List[Tuple], centers: Dict[str, Tuple[float, float, float]],
                                 level, iterations: int = 5) -> Dict[str, Tuple[float, float, float]]:
    try:
        for iteration in range(iterations):
            print(f"\nK-means迭代 {iteration + 1}/{iterations}")
            # 获取实体当前位置
            entities = await get_entities_current_positions(entities)
            # 按实体类型分组
            type_to_positions = {}
            for entity_obj, entity_type, x, y, z in entities:
                if entity_type not in type_to_positions:
                    type_to_positions[entity_type] = []
                type_to_positions[entity_type].append((x, y, z))
            updated_centers = {}
            for entity_type, positions in type_to_positions.items():
                if not positions:
                    print(f"警告: 类型 '{entity_type}' 没有实体")
                    # 保持中心位置不变
                    if entity_type in centers:
                        updated_centers[entity_type] = centers[entity_type]
                    continue
                # 计算质心（所有实体的平均位置）
                avg_x = sum(p[0] for p in positions) / len(positions)
                avg_y = sum(p[1] for p in positions) / len(positions)
                avg_z = sum(p[2] for p in positions) / len(positions)
                # 当前中心位置（如果不存在则使用质心）
                if entity_type in centers:
                    curr_x, curr_y, curr_z = centers[entity_type]
                else:
                    curr_x, curr_y, curr_z = avg_x, avg_y, avg_z
                # 向质心方向移动（移动距离的50%）
                move_factor = 0.5
                new_x = curr_x + (avg_x - curr_x) * move_factor
                new_y = curr_y + (avg_y - curr_y) * move_factor
                new_z = curr_z + (avg_z - curr_z) * move_factor
                # 移除旧的中心方块（如果存在）
                if entity_type in centers:
                    old_x, old_y, old_z = centers[entity_type]
                    await level.set_block(int(old_x), int(old_y), int(old_z), "minecraft:air")
                # 放置新的中心方块
                await level.set_block(int(new_x), int(new_y), int(new_z), CENTER_BLOCK)
                updated_centers[entity_type] = (new_x, new_y, new_z)
                print(f"  中心 '{entity_type}': ({curr_x:.1f}, {curr_y:.1f}, {curr_z:.1f}) -> ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
                print(f"    质心位置: ({avg_x:.1f}, {avg_y:.1f}, {avg_z:.1f}), 实体数量: {len(positions)}")
                await asyncio.sleep(0.2)  # 短暂延迟
            centers = updated_centers
        print("\nK-means迭代完成")
        return centers
    except Exception as e:
        print(f"更新聚类中心失败: {e}")
        raise

async def gather_entities_to_centers(entities: List[Tuple], centers: Dict[str, Tuple[float, float, float]],
                                     area_size: int = 5) -> Dict:
    """
    将实体聚集到对应聚类中心周围的area_size×area_size区域内
    使用entity.teleport()直接传送实体，避免移动过程
    """
    try:
        print(f"\n开始将实体聚集到中心周围{area_size}×{area_size}区域")
        entity_targets = {}  # 存储每个实体的目标位置

        # 按实体类型分组
        type_to_entities = {}
        for entity_obj, entity_type, x, y, z in entities:
            if entity_type not in type_to_entities:
                type_to_entities[entity_type] = []
            type_to_entities[entity_type].append(entity_obj)

        moved_entities = 0
        total_entities = sum(len(objs) for objs in type_to_entities.values())

        for entity_type, entity_objs in type_to_entities.items():
            if entity_type not in centers:
                print(f"警告: 类型 '{entity_type}' 没有对应的聚类中心")
                continue

            center_x, center_y, center_z = centers[entity_type]
            half_size = area_size // 2

            # 根据实体数量自适应调整区域大小，防止过密
            adaptive_area_size = max(area_size, int(math.sqrt(len(entity_objs)) * 3))
            adaptive_half_size = adaptive_area_size // 2
            if adaptive_area_size > area_size:
                print(f"  注意: 实体数量较多，自动扩展聚集区域到 {adaptive_area_size}×{adaptive_area_size} 以防止过密")

            print(f"聚集 '{entity_type}' 的 {len(entity_objs)} 个实体到中心 ({center_x:.1f}, {center_y:.1f}, {center_z:.1f})")

            # 为每个实体创建目标位置列表
            target_positions = []
            for i in range(len(entity_objs)):
                target_x = center_x + random.uniform(-adaptive_half_size, adaptive_half_size)
                target_z = center_z + random.uniform(-adaptive_half_size, adaptive_half_size)
                target_y = center_y + 1.0  # 地面上方1格
                target_positions.append((target_x, target_y, target_z))

            # 直接使用teleport传送实体，避免移动过程
            for idx, (entity_obj, (target_x, target_y, target_z)) in enumerate(zip(entity_objs, target_positions)):
                try:
                    print(f"  传送实体 {moved_entities+1}/{total_entities}: 到 ({target_x:.1f}, {target_y:.1f}, {target_z:.1f})")
                    # 记录实体的目标位置
                    entity_targets[entity_obj] = (target_x, target_y, target_z)
                    # 使用teleport直接传送实体
                    await entity_obj.teleport(target_x, target_y, target_z)
                    moved_entities += 1
                    # 短暂延迟以避免服务器过载
                    await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"    传送实体失败: {e}")
                    continue

            print(f"  类型 '{entity_type}' 完成: {len(entity_objs)} 个实体已传送")

        print(f"实体聚集完成: {moved_entities}/{total_entities} 个实体已传送到目标区域")

        # 短暂等待确保传送完成
        print("等待传送完成...")
        await asyncio.sleep(1.0)

        # 返回实体目标位置映射
        return entity_targets

    except Exception as e:
        print(f"聚集实体失败: {e}")
        import traceback
        traceback.print_exc()
        raise

async def build_classification_fences(level, centers: Dict[str, Tuple[float, float, float]],
                                      player_y: float, fence_size: int = 5) -> None:
    
    try:
        print(f"\n开始在聚类中心周围建造{fence_size}×{fence_size}分类栅栏")
        print(f"栅栏底部高度: {int(player_y)} (玩家高度取整)")

        fence_bottom_y = int(player_y)
        fence_height = 2  # 栅栏高度2格

        for idx, (entity_type, (center_x, center_y, center_z)) in enumerate(centers.items(), 1):
            half_size = fence_size // 2

            # 计算栅栏区域
            x_min = int(center_x - half_size)
            x_max = int(center_x + half_size)
            z_min = int(center_z - half_size)
            z_max = int(center_z + half_size)

            print(f"\n[{idx}/{len(centers)}] 为 '{entity_type}' 建造分类栅栏:")
            print(f"  中心位置: ({center_x:.1f}, {center_y:.1f}, {center_z:.1f})")
            print(f"  栅栏范围: X[{x_min} 到 {x_max}], Z[{z_min} 到 {z_max}]")

            # 清理栅栏区域的地面
            print(f"  清理地面...")
            for x in range(x_min, x_max + 1):
                for z in range(z_min, z_max + 1):
                    # 清理栅栏底部位置
                    await level.set_block(x, fence_bottom_y - 1, z, "minecraft:grass_block")
            await asyncio.sleep(0.1)

            # 建造四边栅栏（高度2格）
            fences_built = 0
            total_fences = (z_max - z_min + 1) * 2 + (x_max - x_min - 1) * 2  # 四边总格数

            # 东边和西边
            for z in range(z_min, z_max + 1):              
                await level.set_blocks(x_min, fence_bottom_y, z, x_min, fence_bottom_y + fence_height - 1, z, FENCE_BLOCK)
                fences_built += 1             
                await level.set_blocks(x_max, fence_bottom_y, z, x_max, fence_bottom_y + fence_height - 1, z, FENCE_BLOCK)
                fences_built += 1
                
            # 北边和南边（跳过角点）
            for x in range(x_min + 1, x_max):
                await level.set_blocks(x, fence_bottom_y, z_min, x, fence_bottom_y + fence_height - 1, z_min, FENCE_BLOCK)
                fences_built += 1             
                await level.set_blocks(x, fence_bottom_y, z_max, x, fence_bottom_y + fence_height - 1, z_max, FENCE_BLOCK)
                fences_built += 1
                

            print(f"  完成: {fences_built}/{total_fences} 个栅栏方块已放置")
            print(f"  栅栏高度: {fence_bottom_y} 到 {fence_bottom_y + fence_height - 1}")

            await asyncio.sleep(0.5)  # 短暂延迟

        print(f"\n分类栅栏建造完成!")
        print(f"  总计: {len(centers)} 个聚类中心的栅栏")
        print(f"  栅栏尺寸: {fence_size}×{fence_size}")
        print(f"  栅栏高度: {fence_height} 格")

    except Exception as e:
        print(f"建造分类栅栏失败: {e}")
        import traceback
        traceback.print_exc()
        raise

async def stabilize_entities(entities: List[Tuple], entity_targets: Dict, duration: float = 30.0, threshold: float = 2.0) -> None:
    
    try:
        print(f"\n开始稳定实体位置，持续时间{duration}秒")
        print(f"偏离阈值: {threshold}格")

        start_time = asyncio.get_event_loop().time()
        corrections = 0

        while asyncio.get_event_loop().time() - start_time < duration:
            for entity_obj, entity_type, _, _, _ in entities:
                if entity_obj not in entity_targets:
                    continue

                target_x, target_y, target_z = entity_targets[entity_obj]

                try:
                    current_x, current_y, current_z = await entity_obj.get_pos()
                    # 计算水平距离（忽略Y轴）
                    dx = current_x - target_x
                    dz = current_z - target_z
                    distance = math.sqrt(dx*dx + dz*dz)

                    if distance > threshold:
                        print(f"  实体 {entity_obj.entity_id} 偏离目标 {distance:.1f} 格，使用teleport传回")
                        await entity_obj.teleport(target_x, target_y, target_z)
                        corrections += 1
                except Exception as e:
                    print(f"  检查实体 {entity_obj.entity_id} 位置失败: {e}")

            # 每次检查后等待1秒
            await asyncio.sleep(1.0)

        print(f"实体稳定完成，共进行 {corrections} 次位置纠正")

    except Exception as e:
        print(f"稳定实体失败: {e}")
        import traceback
        traceback.print_exc()
        raise

async def main():
    # 连接到服务器
    mc = PyModClient()
    print("正在连接到Pycraft服务器...")
    await mc.connect()

    try:
        overworld = mc.overworld()
        print("已连接到主世界")

        # 获取玩家位置
        players = await overworld.get_players()
        if not players:
            print("未找到玩家，使用默认位置")
            center_x, center_y, center_z = 0, 100, 0
        else:
            player = players[0]
            center_x, center_y, center_z = await player.get_pos()
            print(f"玩家位置: ({center_x:.1f}, {center_y:.1f}, {center_z:.1f})")

        # 1. 建造围墙
        print("步骤1: 建造围墙")
        await create_enclosure(overworld, center_x, center_z, center_y, size=ENCLOSURE_SIZE)
        print("等待围墙生成完成...")
        await asyncio.sleep(2.0)

        # 2. 生成实体
        
        print("步骤2: 生成实体")
        entities = await spawn_entities_in_area(mc, overworld, center_x, center_z, center_y,
                                               min_count=MIN_ENTITIES, max_count=MAX_ENTITIES,
                                               entity_types_count=ENTITY_TYPES_COUNT)
        print("等待实体生成完成...")
        await asyncio.sleep(3.0)

        # 提取实体类型列表并统计
        entity_types = list(set(entity_type for _, entity_type, _, _, _ in entities))
        print(f"\n实体生成统计:")
        print(f"  总实体数: {len(entities)}")
        print(f"  实体种类: {len(entity_types)} 种")

        # 统计每种类型的数量
        type_counts = {}
        for _, entity_type, _, _, _ in entities:
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        for entity_type, count in type_counts.items():
            print(f"    {entity_type}: {count} 个")


        # 3. 初始化聚类中心
       
        print("步骤3: 初始化聚类中心")
        centers = await init_cluster_centers(overworld, center_x, center_z, center_y, entity_types, size=ENCLOSURE_SIZE)
        print("等待中心初始化完成...")
        await asyncio.sleep(1.5)

        # 4. K-means迭代
        
        print("步骤4: K-means迭代")
        print(f"开始 {KMEANS_ITERATIONS} 次迭代，聚类中心将向实体密集区域移动...")
        centers = await update_cluster_centers(entities, centers, overworld, iterations=KMEANS_ITERATIONS)
        print("K-means迭代完成!")
        await asyncio.sleep(1.5)

        # 5. 将实体聚集到中心周围
        print("步骤5: 实体向中心聚集")
        print(f"使用 entity.teleport() 将实体聚集到中心周围{GATHER_AREA_SIZE}×{GATHER_AREA_SIZE}区域...")
        entity_targets = await gather_entities_to_centers(entities, centers, area_size=GATHER_AREA_SIZE)
        print("实体聚集完成，开始稳定实体位置...")
        await stabilize_entities(entities, entity_targets, duration=30.0)

        # 6. 建造分类栅栏
        print("步骤6: 建造分类栅栏")
        print(f"在每个聚类中心周围建造{CLASSIFICATION_FENCE_SIZE}×{CLASSIFICATION_FENCE_SIZE}分类栅栏...")
        await build_classification_fences(overworld, centers, center_y, fence_size=CLASSIFICATION_FENCE_SIZE)
        print("分类栅栏建造完成!")
        await asyncio.sleep(1.0)

        print("\n最终聚类中心位置:")
        for entity_type, (x, y, z) in centers.items():
            count = type_counts.get(entity_type, 0)
            print(f"  {entity_type}: ({x:.1f}, {y:.1f}, {z:.1f}) - {count} 个实体")

    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n断开服务器连接...")
        await mc.close()
if __name__ == "__main__":
    asyncio.run(main())