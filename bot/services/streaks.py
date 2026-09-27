from dataclasses import dataclass, replace
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakState:
    current: int
    longest: int
    last_solved: date | None


def record_solve(state: StreakState, today: date) -> StreakState:
    """Return the new streak state after a user solves today's problem."""
    if state.last_solved == today:
        return state

    yesterday = today - timedelta(days=1)
    if state.last_solved == yesterday:
        new_current = state.current + 1
    else:
        new_current = 1

    return replace(
        state,
        current=new_current,
        longest=max(state.longest, new_current),
        last_solved=today,
    )


def displayed_streak(state: StreakState, today: date) -> int:
    """Return the streak to show. A streak is alive if solved today or yesterday."""
    if state.last_solved is None:
        return 0

    yesterday = today - timedelta(days=1)

    if state.last_solved in (today, yesterday):
        return state.current
    return 0
