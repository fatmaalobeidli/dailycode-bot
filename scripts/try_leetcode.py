import asyncio

import aiohttp

from bot.services.leetcode import fetch_daily


async def main():
    async with aiohttp.ClientSession() as session:
        problem = await fetch_daily(session)
        print(problem)


asyncio.run(main())
