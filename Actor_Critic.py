import asyncio
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import math

class ActorCritic(nn.Module):
    def __init__(self, state_dim=8, action_dim=8):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        self.actor = nn.Linear(128, action_dim)
        self.critic = nn.Linear(128, 1)

    def forward(self, x):
        x = self.net(x)
        return self.actor(x), self.critic(x)

    def act(self, state):
        logits, value = self.forward(state)
        probs = F.softmax(logits, dim=-1)
        dist = torch.distributions.Categorical(probs)
        action = dist.sample()
        return action.item(), dist.log_prob(action), value


# 环境
class MCEnv:
    def __init__(self, player, level):
        self.player = player
        self.level = level

        self.prev_dist = None
        self.prev_monster_health = None
        self.prev_player_health = None

        self.step_count = 0
        self.max_steps = 150

        self.spawn_point = None
        self.world_prepared = False

    # 平坦环境和高围墙
    async def prepare_flat_world(self, center, radius=10, wall_height=4):
        cx, cy, cz = map(int, center)

        # 清空空间
        await self.level.set_blocks(
            cx - radius, cy, cz - radius,
            cx + radius, cy + 5, cz + radius,
            "minecraft:air"
        )

        # 地板
        await self.level.set_blocks(
            cx - radius, cy - 1, cz - radius,
            cx + radius, cy - 1, cz + radius,
            "minecraft:stone"
        )

        # 围墙
        for h in range(wall_height):
            y = cy + h

            await self.level.set_blocks(cx - radius, y, cz - radius,
                                        cx + radius, y, cz - radius,
                                        "minecraft:glass")

            await self.level.set_blocks(cx - radius, y, cz + radius,
                                        cx + radius, y, cz + radius,
                                        "minecraft:glass")

            await self.level.set_blocks(cx - radius, y, cz - radius,
                                        cx - radius, y, cz + radius,
                                        "minecraft:glass")

            await self.level.set_blocks(cx + radius, y, cz - radius,
                                        cx + radius, y, cz + radius,
                                        "minecraft:glass")

    # 清除怪物
    async def clear_monsters(self):
        entities = await self.level.get_entities("monster") 

        for e in entities:
            try:
                await e.remove()
            except:
                pass

        await asyncio.sleep(0.05)

    # 工具
    async def get_entities(self):
        return await self.level.get_entities("all")

    async def get_player_health(self):
        entities = await self.get_entities()
        for e in entities:
            if e.entity_id == self.player.entity_id:
                return e.health
        return 20.0

    async def get_nearest_monster(self):
        monsters = await self.level.get_entities("monster")

        if not monsters:
            return None

        px, py, pz = await self.player.get_pos()

        def dist(e):
            ex, ey, ez = e.pos
            return (ex - px)**2 + (ey - py)**2 + (ez - pz)**2

        return min(monsters, key=dist)

    # reset
    async def reset(self):
        self.step_count = 0

        if self.spawn_point is None:
            self.spawn_point = await self.player.get_pos()

        px, py, pz = self.spawn_point

        # 1. 清怪
        await self.clear_monsters()

        # 2. 构建环境
        if not self.world_prepared:
            await self.prepare_flat_world((px, py, pz))
            self.world_prepared = True

        # 3. 重置玩家
        await self.player.teleport(px, py, pz)

        # 4. 生成怪物
        await self.level.spawn_entity("spider", px + 4, py, pz + 4)

        await asyncio.sleep(0.2)

        state = await self.get_state()

        self.prev_dist = state[3].item()
        self.prev_monster_health = state[5].item()
        self.prev_player_health = await self.get_player_health()

        return state

    # state
    async def get_state(self):
        m = await self.get_nearest_monster()
        if m is None:
            return torch.zeros(8)

        px, py, pz = await self.player.get_pos()
        mx, my, mz = m.pos

        dx, dy, dz = mx - px, my - py, mz - pz
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        return torch.tensor([
            dx / 20,
            dy / 10,
            dz / 20,
            dist / 20,
            1.0,
            m.health / 20,
            1.0 if dist < 3 else 0.0,
            1.0 if dist < 1.5 else 0.0
        ], dtype=torch.float32)

    # step
    async def step(self, action):
        self.step_count += 1
        reward = 0.0

        px, py, pz = await self.player.get_pos()
        m = await self.get_nearest_monster()

        if m is None:
            return torch.zeros(8), -10, True

        mx, my, mz = m.pos

        # move
        if action == 0:
            await self.player.move_to(mx, py, mz)

        elif action == 1:
            dx = px - mx
            dz = pz - mz
            await self.player.move_to(px + dx, py, pz + dz)

        elif action == 2:
            await self.player.move_to(px - 1, py, pz)

        elif action == 3:
            await self.player.move_to(px + 1, py, pz)

        elif action == 4:
            await self.player.move_to(px - 1, py, pz - 1)

        elif action == 5:
            await self.player.move_to(px + 1, py, pz - 1)

        elif action == 6:
            yaw = math.degrees(math.atan2(-(mx - px), (mz - pz)))
            await self.player.set_rotation(yaw, 20)

        elif action == 7:
            await self.player.attack(m)

        await asyncio.sleep(0.1)

        # 更新状态
        next_state = await self.get_state()

        dist = next_state[3].item() * 20
        monster_health = next_state[5].item()
        player_health = await self.get_player_health()

        # reward
        reward += (self.prev_dist - dist) * 0.5
        self.prev_dist = dist

        damage = self.prev_monster_health - monster_health
        if damage > 0:
            reward += damage * 10
        self.prev_monster_health = monster_health

        damage_taken = self.prev_player_health - player_health
        if damage_taken > 0:
            reward -= damage_taken * 8
        self.prev_player_health = player_health

        if 2 < dist < 3:
            reward += 0.5
        if dist < 1.5:
            reward -= 1.5

        if action == 7 and dist > 3:
            reward -= 1.0

        # 终止
        if monster_health <= 0:
            return next_state, reward + 20, True

        if player_health <= 0:
            return next_state, reward - 20, True

        if self.step_count > self.max_steps:
            return next_state, reward, True

        reward -= 0.01
        return next_state, reward, False


# 训练
async def train(env, model, episodes=200):
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    gamma = 0.99

    for ep in range(episodes):
        state = await env.reset()

        log_probs, values, rewards = [], [], []
        total_reward = 0

        for _ in range(env.max_steps):
            action, log_prob, value = model.act(state.unsqueeze(0))
            next_state, reward, done = await env.step(action)

            log_probs.append(log_prob)
            values.append(value)
            rewards.append(torch.tensor([reward]))

            total_reward += reward
            state = next_state

            if done:
                break

        returns = []
        G = 0
        for r in reversed(rewards):
            G = r + gamma * G
            returns.insert(0, G)

        returns = torch.cat(returns).detach()
        values = torch.cat(values).squeeze()
        advantage = returns - values

        loss = -(torch.stack(log_probs) * advantage.detach()).mean() + 0.5 * advantage.pow(2).mean()

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        print(f"[EP {ep}] reward={total_reward:.2f}")


async def main():
    from pycraft import PyModClient

    client = PyModClient()
    await client.connect()

    try:
        level = client.overworld()
        player = (await level.get_players())[0]

        env = MCEnv(player, level)
        model = ActorCritic()

        await train(env, model)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())