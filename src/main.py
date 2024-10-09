import asyncio
import json
from loguru import logger
from httpx import AsyncClient
import random


def get_random_proxy():
    with open("data/proxies.txt", "r") as file:
        proxies = random.choice(file.read().splitlines())

    return {"all://": proxies}


async def worker(q: asyncio.Queue[str]):
    while not q.empty():
        address = await q.get()

        batch = {"0": {"json": {"chainId": 10, "address": address, "id": "5"}}}
        batch_length = batch.__len__()

        try:
            cli = AsyncClient(proxies=get_random_proxy())

            response = await cli.get(
                url="https://prod-gateway-backend-mainnet.optimism.io/api/v0/eligibility.eligibilityAmounts",
                params={"batch": batch_length, "input": json.dumps(batch)},
                timeout=60,
            )
            data = response.json()

            if data != [{"result": {"data": {"json": None}}}]:
                total_amount = (
                    data[0]
                    .get("result", {})
                    .get("data", {})
                    .get("json", {})
                    .get("totalAmount", 0)
                )
                logger.success(f"Address {address} has {total_amount/10**18:.2f} OP")
                with open("op5.txt", "a") as file:
                    file.write(f"{address}:{total_amount/10**18:.2f}\n")
            else:
                logger.error(f"Address {address} is not eligible for OP")
        except Exception as error:
            logger.error(f"Address {address} is not eligible for OP: {error}")
            await q.put(address)
            continue

        q.task_done()


async def main(addresses: list[str]):
    q: asyncio.Queue[str] = asyncio.Queue()

    for address in addresses:
        if address:
            q.put_nowait(address)

    tasks = []
    for _ in range(int(input("Enter number of workers: "))):
        tasks.append(asyncio.create_task(worker(q)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
       with open("data/addresses.txt", "r") as file:
            addresses = file.read().splitlines()
    except FileNotFoundError:
        logger.error("File addresses.txt not found")

        with open(input("Enter file name with addresses: "), "r") as file:
            addresses = file.read().splitlines()

    try:
        asyncio.run(main(addresses))
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Program was interrupted by user")
