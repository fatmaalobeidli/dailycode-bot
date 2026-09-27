from datetime import date, datetime, timezone

from bot.services.leetcode import AcceptedSubmission
from bot.services.solves import find_solve_on, points_for, was_solved_on

TODAY = date(2026, 9, 27)


def sub(slug: str, *args: int) -> AcceptedSubmission:
    return AcceptedSubmission(slug=slug, solved_at=datetime(*args, tzinfo=timezone.utc))


def test_solved_today():
    subs = [sub("two-sum", 2026, 9, 27, 14, 0)]
    assert was_solved_on(subs, "two-sum", TODAY)


def test_solved_yesterday_does_not_count():
    subs = [sub("two-sum", 2026, 9, 26, 14, 0)]
    assert not was_solved_on(subs, "two-sum", TODAY)


def test_other_problem_today_does_not_count():
    subs = [sub("valid-parentheses", 2026, 9, 27, 14, 0)]
    assert not was_solved_on(subs, "two-sum", TODAY)


def test_empty_list():
    assert not was_solved_on([], "two-sum", TODAY)


def test_just_before_midnight_counts_for_that_day():
    subs = [sub("two-sum", 2026, 9, 27, 23, 59)]
    assert was_solved_on(subs, "two-sum", TODAY)
    assert not was_solved_on(subs, "two-sum", date(2026, 9, 28))


def test_just_after_midnight_counts_for_next_day():
    subs = [sub("two-sum", 2026, 9, 28, 0, 1)]
    assert not was_solved_on(subs, "two-sum", TODAY)
    assert was_solved_on(subs, "two-sum", date(2026, 9, 28))


def test_find_returns_matching_submission():
    old = sub("two-sum", 2026, 3, 14, 9, 0)
    today = sub("two-sum", 2026, 9, 27, 14, 0)
    assert find_solve_on([old, today], "two-sum", TODAY) == today


def test_points_for():
    assert points_for("Easy") == 1
    assert points_for("Medium") == 2
    assert points_for("Hard") == 3
    assert points_for("Unknown") == 0
