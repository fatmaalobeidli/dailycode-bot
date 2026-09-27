import asyncio
from dataclasses import dataclass

import aiohttp

GRAPHQL_URL = "https://leetcode.com/graphql"

DAILY_QUERY = """
query questionOfToday {
    activeDailyCodingChallengeQuestion {
        date
        link
        question {
            title
            titleSlug
            difficulty
            acRate
            topicTags { name }
        }
    }
}
"""

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (DailyCodeBot)",
}


class LeetCodeError(Exception):
    """Raised when LeetCode can't be reached or returns unexpected data"""


@dataclass(frozen=True)
class DailyProblem:
    date: str
    title: str
    slug: str
    difficulty: str
    url: str
    ac_rate: float
    tags: tuple[str, ...]


def parse_daily(data: dict) -> DailyProblem:
    """Turn the raw GraphQL JSON into a DailyProblem."""
    try:
        daily = data["data"]["activeDailyCodingChallengeQuestion"]

        if daily is None:
            raise LeetCodeError("No daily challenge was returned")
        q = daily["question"]
        return DailyProblem(
            date=daily["date"],
            title=q["title"],
            slug=q["titleSlug"],
            difficulty=q["difficulty"],
            url="https://leetcode.com" + daily["link"],
            ac_rate=round(q["acRate"], 1),
            tags=tuple(tag["name"] for tag in q["topicTags"]),
        )
    except (KeyError, TypeError) as e:
        raise LeetCodeError(f"Unexpected response format: {e}") from e


async def fetch_daily(session: aiohttp.ClientSession) -> DailyProblem:
    """Fetch today's daily problem from LeetCode."""
    payload = {"query": DAILY_QUERY, "operationName": "questionOfToday"}
    try:
        async with session.post(
            GRAPHQL_URL,
            json=payload,
            headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                raise LeetCodeError(f"LeetCode returned HTTP {resp.status}")
            data = await resp.json()
            if "errors" in data:
                raise LeetCodeError(f"Leetcode GraphQL error: {data['errors']}")
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise LeetCodeError(f"Network error: {e}") from e
    except ValueError as e:
        raise LeetCodeError(f"Invalid JSON from LeetCode: {e}") from e

    return parse_daily(data)
