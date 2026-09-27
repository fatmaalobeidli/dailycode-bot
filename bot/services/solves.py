from collections.abc import Iterable
from datetime import date

from bot.services.leetcode import AcceptedSubmission

POINTS_BY_DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3}


def find_solve_on(
    submissions: Iterable[AcceptedSubmission], slug: str, day: date
) -> AcceptedSubmission | None:
    """
    Return the accepted submission of `slug` on `day` (UTC), or None.
    Solves of the same problem on earlier days don't count.
    """
    for sub in submissions:
        if sub.slug == slug and sub.solved_at.date() == day:
            return sub
    return None


def was_solved_on(
    submissions: Iterable[AcceptedSubmission], slug: str, day: date
) -> bool:
    """True if 'slug' was accepted on 'day' (UTC)."""
    return find_solve_on(submissions, slug, day) is not None


def points_for(difficulty: str) -> int:
    """Points awarded for solving a problem of the given difficulty."""
    return POINTS_BY_DIFFICULTY.get(difficulty, 0)
