import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

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

USER_QUERY = """
query userPublicProfile($username: String!) {
    matchedUser(username: $username) {
        username
    }
}
"""

RECENT_AC_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
    recentAcSubmissionList(username: $username, limit: $limit) {
        titleSlug
        timestamp
    }
}
"""

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (DailyCodeBot)",
}


class LeetCodeError(Exception):
    """Raised when LeetCode can't be reached or returns unexpected data."""


@dataclass(frozen=True)
class DailyProblem:
    date: str
    title: str
    slug: str
    difficulty: str
    url: str
    ac_rate: float
    tags: tuple[str, ...]


@dataclass(frozen=True)
class AcceptedSubmission:
    slug: str
    solved_at: datetime  # timezone aware, UTC


# HTTP
async def _post_graphql(session: aiohttp.ClientSession, payload: dict) -> dict:
    """Send one GraphQL request to LeetCode and return the JSON body."""
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
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise LeetCodeError(f"Network error: {e}") from e
    except ValueError as e:
        raise LeetCodeError(f"Invalid JSON from LeetCode: {e}") from e

    # GraphQL can return partial data together with errors (ex "user does not exist")
    # only treat it as a failure if there is no usable data at all
    if data.get("errors") and not data.get("data"):
        raise LeetCodeError(f"LeetCode GraphQL error: {data['errors']}")
    return data


# Daily problem
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
    data = await _post_graphql(session, payload)
    return parse_daily(data)


# User lookup
def parse_user_exists(data: dict) -> bool:
    """True if the GraphQL response contains a matching user."""
    try:
        return data["data"]["matchedUser"] is not None
    except (KeyError, TypeError) as e:
        raise LeetCodeError(f"Unexpected response format: {e}") from e


async def user_exists(session: aiohttp.ClientSession, username: str) -> bool:
    """Check whether a LeetCode username exists."""
    payload = {
        "query": USER_QUERY,
        "operationName": "userPublicProfile",
        "variables": {"username": username},
    }
    data = await _post_graphql(session, payload)
    return parse_user_exists(data)


# Recent accepted submissions
def parse_recent_accepted(data: dict) -> list[AcceptedSubmission]:
    """Turn the raw GraphQL JSON into a list of AcceptedSubmission (UTC)."""
    try:
        items = data["data"]["recentAcSubmissionList"]
        if items is None:
            return []
        return [
            AcceptedSubmission(
                slug=item["titleSlug"],
                solved_at=datetime.fromtimestamp(
                    int(item["timestamp"]), tz=timezone.utc
                ),
            )
            for item in items
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise LeetCodeError(f"Unexpected response format: {e}") from e


async def fetch_recent_accepted(
    session: aiohttp.ClientSession, username: str, limit: int = 20
) -> list[AcceptedSubmission]:
    """Fetch a user's most recent accepted (public) submissions."""
    payload = {
        "query": RECENT_AC_QUERY,
        "operationName": "recentAcSubmissions",
        "variables": {"username": username, "limit": limit},
    }
    data = await _post_graphql(session, payload)
    return parse_recent_accepted(data)
