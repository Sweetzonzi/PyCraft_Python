from pycraft import PyModClient
import asyncio
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

X_MAX, Z_MAX, Y_MAX = 4, 4, 6
AIR = "minecraft:air"
STONE = "minecraft:stone"
DIAMOND = "minecraft:diamond_ore"
REDSTONE = "minecraft:redstone_block"

START_POS = (1, 1, 0)          # (x, z, y)
DIAMOND_POS = (2, 1, 3)         # (x, z, y)
TRAPS = [(0, 1, 2), (3, 3, 4)]  # (x, z, y)

GAMMA = 0.99
LAMBDA = 0.95       # GAE 参数
CLIP_EPS = 0.2      # PPO clip 范围
EPOCHS = 4          # 每轮数据重复利用次数
BATCH_SIZE = 32     # 迷你批次大小
LR = 3e-4
ENTROPY_COEFF = 0.01

# 矿井重置
async def reset_mine(level, base_x, base_y, base_z):
    for y in range(Y_MAX):
        for x in range(X_MAX):
            for z in range(Z_MAX):
                await level.set_block(base_x + x, base_y - y, base_z + z, STONE)
    dx, dz, dy = DIAMOND_POS
    await level.set_block(base_x + dx, base_y - dy, base_z + dz, DIAMOND)
    for x, z, y in TRAPS:
        await level.set_block(base_x + x, base_y - y, base_z + z, REDSTONE)

# AI网络
class MiningAI(nn.Module):
    def __init__(self, action_dim=6):
        super().__init__()
        self.action_dim = action_dim
        self.shared = nn.Sequential(
            nn.Linear(X_MAX * Z_MAX * Y_MAX, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        self.actor = nn.Linear(128, action_dim)
        self.critic = nn.Linear(128, 1)

    def forward(self, x):
        feat = self.shared(x)
        logits = self.actor(feat)
        value = self.critic(feat)
        return logits, value

class Agent:
    def __init__(self, action_dim=6):
        self.model = MiningAI(action_dim)
        self.opt = optim.Adam(self.model.parameters(), lr=LR)

    def get_valid_mask(self, env):
        """返回一个布尔张量，True表示该动作合法"""
        dirs = [(0, 1), (0, -1), (-1, 0), (1, 0), (0, 0, 1), (0, 0, -1)]
        mask = torch.zeros(6, dtype=torch.bool)
        for i, d in enumerate(dirs):
            if len(d) == 2:  # 水平移动
                dx, dz = d
                tx, tz = env.x + dx, env.z + dz
                if 0 <= tx < X_MAX and 0 <= tz < Z_MAX:
                    if env.grid[env.y, tx, tz] != 0:
                        mask[i] = True
            else:  # 上下移动
                dy = d[2]
                ty = env.y + dy
                if 0 <= ty < Y_MAX:
                    if env.grid[ty, env.x, env.z] != 0:
                        mask[i] = True
        return mask

    def act(self, state, env):
        s = torch.FloatTensor(state).unsqueeze(0)
        logits, value = self.model(s)
        valid_mask = self.get_valid_mask(env)

        # 将非法动作设为 -1e9 而非 -inf，避免 Categorical 报错
        masked_logits = logits.clone()
        masked_logits[0, ~valid_mask] = -1e9

        # 防御：如果所有动作都非法（理论上不应发生），则随机选一个
        if not valid_mask.any():
            print("警告：无合法动作，随机选择动作")
            action = torch.randint(0, 6, (1,)).item()
            # 确保 log_prob 也是 tensor，以便统一调用 .item()
            log_prob = torch.tensor(0.0)
        else:
            dist = Categorical(logits=masked_logits)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        return action, log_prob.item(), value.item()

    def learn(self, trajectories):
        states = torch.FloatTensor(np.array([t[0] for t in trajectories]))
        actions = torch.LongTensor([t[1] for t in trajectories])
        rewards = torch.FloatTensor([t[2] for t in trajectories])
        dones = torch.FloatTensor([t[3] for t in trajectories])
        old_log_probs = torch.FloatTensor([t[4] for t in trajectories])
        old_values = torch.FloatTensor([t[5] for t in trajectories])

        # GAE 计算优势
        advantages = []
        gae = 0
        values = old_values.detach().numpy()
        for t in reversed(range(len(rewards))):
            next_val = values[t+1] if t+1 < len(rewards) else 0
            delta = rewards[t] + GAMMA * next_val * (1 - dones[t]) - values[t]
            gae = delta + GAMMA * LAMBDA * (1 - dones[t]) * gae
            advantages.insert(0, gae)
        advantages = torch.FloatTensor(advantages)
        returns = advantages + old_values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO 多轮更新
        dataset_size = len(states)
        for _ in range(EPOCHS):
            indices = np.random.permutation(dataset_size)
            for start in range(0, dataset_size, BATCH_SIZE):
                idx = indices[start:start+BATCH_SIZE]
                batch_states = states[idx]
                batch_actions = actions[idx]
                batch_old_log_probs = old_log_probs[idx]
                batch_advantages = advantages[idx]
                batch_returns = returns[idx]

                logits, values = self.model(batch_states)
                dist = Categorical(logits=logits)
                new_log_probs = dist.log_prob(batch_actions)
                entropy = dist.entropy().mean()

                ratio = (new_log_probs - batch_old_log_probs).exp()
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS) * batch_advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                critic_loss = (batch_returns - values.squeeze()).pow(2).mean()
                loss = actor_loss + 0.5 * critic_loss - ENTROPY_COEFF * entropy

                self.opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.opt.step()

# 环境
class MineEnv:
    def __init__(self):
        self.grid = np.ones((Y_MAX, X_MAX, Z_MAX), dtype=int)
        x, z, y = DIAMOND_POS
        self.grid[y, x, z] = 3
        for xt, zt, yt in TRAPS:
            self.grid[yt, xt, zt] = 2
        self.x, self.z, self.y = START_POS
        self.step_count = 0
        self.done = False

    def reset(self):
        self.__init__()
        return self.grid.flatten() / 3.0   # 归一化

    def step(self, action):
        self.step_count += 1
        dirs = [(0,1), (0,-1), (-1,0), (1,0), (0,0,1), (0,0,-1)]
        d = dirs[action]
        if len(d) == 2:
            dx, dz = d
            tx, tz = self.x + dx, self.z + dz
            if not (0 <= tx < X_MAX and 0 <= tz < Z_MAX):
                return self.grid.flatten() / 3.0, -10, True
            target = self.grid[self.y, tx, tz]
            if target == 0:
                return self.grid.flatten() / 3.0, -10, True
            reward = 0
            if target == 1:
                reward = 1
                self.x, self.z = tx, tz
            elif target == 2:
                reward = -20
                self.done = True
            elif target == 3:
                reward = 100 - self.step_count
                self.done = True
            self.grid[self.y, tx, tz] = 0
        else:
            dy = d[2]
            ty = self.y + dy
            if not (0 <= ty < Y_MAX):
                return self.grid.flatten() / 3.0, -10, True
            target = self.grid[ty, self.x, self.z]
            if target == 0:
                return self.grid.flatten() / 3.0, -10, True
            reward = 0
            if target == 1:
                reward = 1
                self.y = ty
            elif target == 2:
                reward = -20
                self.done = True
            elif target == 3:
                reward = 100 - self.step_count
                self.done = True
            self.grid[ty, self.x, self.z] = 0
        return self.grid.flatten() / 3.0, reward, self.done

# 渲染
async def render(level, x, z, y, bx, by, bz, env):
    grid = env.grid.reshape(Y_MAX, X_MAX, Z_MAX)
    for iy in range(Y_MAX):
        for ix in range(X_MAX):
            for iz in range(Z_MAX):
                if grid[iy, ix, iz] == 0:
                    await level.set_block(bx + ix, by - iy, bz + iz, AIR)
    await player.teleport(bx + x + 0.5, by - y + 1.2, bz + z + 0.5)

# 主程序
async def main():
    global player
    mc = PyModClient(port=9586)
    await mc.connect()
    level = mc.overworld()
    player = (await level.get_players())[0]
    bx, by, bz = map(int, await player.get_pos())

    await reset_mine(level, bx, by, bz)
    env = MineEnv()
    agent = Agent(action_dim=6)

    for episode in range(100):
        await reset_mine(level, bx, by, bz)
        state = env.reset()
        total_reward = 0
        trajectory = []

        while True:
            action, log_prob, value = agent.act(state, env)
            next_state, reward, done = env.step(action)
            trajectory.append((state, action, reward, done, log_prob, value))
            await render(level, env.x, env.z, env.y, bx, by, bz, env)
            await asyncio.sleep(0.1)

            total_reward += reward
            state = next_state

            if done:
                if reward > 50:
                    status = f"挖到钻石！步数：{env.step_count}"
                else:
                    status = "踩到红石或越界"
                print(f"第{episode+1}轮 | {status} | 总奖励：{total_reward:.1f} | 步数：{env.step_count}")
                break

        agent.learn(trajectory)

        if episode % 50 == 0 and episode > 0:
            print(f"--- 已训练 {episode} 轮 ---")

    await mc.close()

if __name__ == "__main__":
    asyncio.run(main())