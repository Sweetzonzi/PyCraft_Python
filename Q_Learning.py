import random
import asyncio
from pycraft import PyModClient

class QLearningTable:
    def __init__(self, actions, learning_rate=0.1, reward_decay=0.9, e_greedy=0.9):
        self.actions = actions              # [0,1,2,3]
        self.lr = learning_rate
        self.gamma = reward_decay
        self.epsilon = e_greedy
        self.q = {}                     

    def choose_action(self, state):
        self.check_state_exist(state)

        if random.random() < self.epsilon:
            q_list = self.q[state]
            max_q = max(q_list)
            best_actions = [i for i, q in enumerate(q_list) if q == max_q]
            action = random.choice(best_actions)
        else:
            action = random.choice(self.actions)

        return action

    def learn(self, s, a, r, s_):
        self.check_state_exist(s_)
        q_predict = self.q[s][a]

        if s_ != 'terminal':
            q_target = r + self.gamma * max(self.q[s_])
        else:
            q_target = r

        self.q[s][a] += self.lr * (q_target - q_predict)

    def check_state_exist(self, state):
        if state not in self.q:
            self.q[state] = [0.0 for _ in self.actions]



class Maze:
    def __init__(self, client, level, agent):
        self.client = client
        self.level = level
        self.agent = agent

        self.origin = (0, 64, 0)

        self.maze = [
            [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 1, 1, 0, 1, 1, 0, 0],
            [0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
            [0, 1, 0, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            [0, 1, 0, 0, 1, 0, 0, 0, 1, 0]
        ]

        self.rows = len(self.maze)
        self.cols = len(self.maze[0])

        self.start = (0, 0)
        self.goal = (9, 9)

        self.n_actions = 4

    # 构建迷宫
    async def build_maze(self):
        ox, oy, oz = self.origin

        # 清空区域
        await self.level.set_blocks(
            ox - 5, oy - 2, oz - 5,
            ox + 20, oy + 10, oz + 20,
            "minecraft:air"
        )

        # 地面和墙
        for r in range(self.rows):
            for c in range(self.cols):
                # 地面
                await self.level.set_block(
                    ox + r, oy, oz + c,
                    "minecraft:grass_block"
                )

                if self.maze[r][c] == 1:
                    # 墙
                    await self.level.set_blocks(
                        ox + r, oy + 1, oz + c,
                        ox + r, oy + 3, oz + c,
                        "minecraft:stone"
                    )

        # 外围墙
        await self.level.set_blocks(ox - 1, oy, oz - 1, ox + self.rows, oy + 3, oz - 1, "minecraft:stone")
        await self.level.set_blocks(ox - 1, oy, oz + self.cols, ox + self.rows, oy + 3, oz + self.cols, "minecraft:stone")
        await self.level.set_blocks(ox - 1, oy, oz, ox - 1, oy + 3, oz + self.cols, "minecraft:stone")
        await self.level.set_blocks(ox + self.rows, oy, oz, ox + self.rows, oy + 3, oz + self.cols, "minecraft:stone")

        # 终点
        gx, gz = self.goal
        await self.level.set_block(
            ox + gx, oy, oz + gz,
            "minecraft:gold_block"
        )

    # reset
    async def reset(self):
        self.agent_pos = self.start
        await self.teleport_agent()
        return self.agent_pos

    async def teleport_agent(self):
        x, z = self.agent_pos
        ox, oy, oz = self.origin

        await self.agent.teleport(
            ox + x,
            oy + 1,
            oz + z
        )

    # step
    async def step(self, action):
        x, z = self.agent_pos

        moves = {
            0: (0, -1),
            1: (0, 1),
            2: (-1, 0),
            3: (1, 0)
        }

        dx, dz = moves[action]
        nx, nz = x + dx, z + dz

        reward = -0.04
        done = False

        if nx < 0 or nx >= self.rows or nz < 0 or nz >= self.cols:
            reward = -1

        elif self.maze[nx][nz] == 1:
            reward = -1

        else:
            self.agent_pos = (nx, nz)
            await self.teleport_agent()

            if self.agent_pos == self.goal:
                reward = 1
                done = True

        await asyncio.sleep(0.2)
        return self.agent_pos, reward, done
    
async def update(env, RL):
    for episode in range(100):
        observation = await env.reset()
        episode_reward = 0
        step_count = 0 # 统计步数
        while True:
            action = RL.choose_action(str(observation))
            observation_, reward, done = await env.step(action)
            RL.learn(str(observation), action, reward, str(observation_))
            observation = observation_
            episode_reward += reward
            step_count += 1
            if done:
                break
        # 输出每一轮结果
        print(f"[Episode {episode}] reward = {episode_reward:.3f}, steps = {step_count}")

async def main():
    client = PyModClient()
    await client.connect()
    try:
        level = client.overworld()
        players = await level.get_players()
        agent = players[0]
        await agent.set_perspective(0)
        env = Maze(client, level, agent)
        await env.build_maze()
        RL = QLearningTable(actions=list(range(env.n_actions)))
        await update(env, RL)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())