import asyncio
import json
from pycraft import PyModClient
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BLOCK_IDS = [
    1, 2, 3, 5, 12, 18, 35,
    41, 45, 46, 48,
    56, 57, 73,
    79, 80, 89,
    103, 247
]

PATCH_SIZE = 5
GAP = 3
BLOCKS_PER_ROW = 5


async def generate_block_field():
    client = PyModClient()
    await client.connect()
    overworld = client.overworld()
    players = await overworld.get_players()
    player = players[0]

    with open(os.path.join(BASE_DIR, "blockid_to_name.json"), "r") as f:
        block_id_to_name = {int(k): v for k, v in json.load(f).items()}

    x, y, z = await player.get_pos()
    start_x = x - (BLOCKS_PER_ROW * (PATCH_SIZE + GAP)) // 2
    start_y = y - 1
    start_z = z + 5


    for i, block_id in enumerate(BLOCK_IDS):
        row = i // BLOCKS_PER_ROW
        col = i % BLOCKS_PER_ROW
        x0 = start_x + col * (PATCH_SIZE + GAP)
        z0 = start_z + row * (PATCH_SIZE + GAP)
        block_name = block_id_to_name.get(block_id, "UNKNOWN")

        await overworld.set_blocks(
            x0, start_y, z0,
            x0 + PATCH_SIZE - 1, start_y, z0 + PATCH_SIZE - 1,
            block_name
        )

        await asyncio.sleep(0.05)

    await client.close()


if __name__ == "__main__":
    asyncio.run(generate_block_field())