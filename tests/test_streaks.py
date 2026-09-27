from datetime import date

from bot.services.streaks import StreakState, displayed_streak, record_solve

TODAY = date(2026, 9, 27)
YESTERDAY = date(2026, 9, 26)
LAST_WEEK = date(2026, 9, 20)


# record_solve


def test_first_solve_ever_starts_streak_at_1():
    state = StreakState(current=0, longest=0, last_solved=None)
    new = record_solve(state, TODAY)
    assert new == StreakState(current=1, longest=1, last_solved=TODAY)


def test_solve_after_yesterday_increments_streak():
    state = StreakState(current=5, longest=5, last_solved=YESTERDAY)
    new = record_solve(state, TODAY)
    assert new == StreakState(current=6, longest=6, last_solved=TODAY)


def test_solve_after_gap_resets_streak_to_1():
    state = StreakState(current=5, longest=8, last_solved=LAST_WEEK)
    new = record_solve(state, TODAY)
    assert new == StreakState(current=1, longest=8, last_solved=TODAY)


def test_solving_twice_same_day_changes_nothing():
    state = StreakState(current=3, longest=3, last_solved=TODAY)
    new = record_solve(state, TODAY)
    assert new == state


def test_longest_is_kept_when_current_is_lower():
    state = StreakState(current=2, longest=10, last_solved=YESTERDAY)
    new = record_solve(state, TODAY)
    assert new.current == 3
    assert new.longest == 10


def test_record_solve_does_not_mutate_input():
    state = StreakState(current=1, longest=1, last_solved=YESTERDAY)
    record_solve(state, TODAY)
    assert state.current == 1


def test_streak_across_month_boundary():
    state = StreakState(current=4, longest=4, last_solved=date(2026, 9, 30))
    new = record_solve(state, date(2026, 10, 1))
    assert new.current == 5


# displayed_streak


def test_display_streak_solved_today():
    state = StreakState(current=7, longest=7, last_solved=TODAY)
    assert displayed_streak(state, TODAY) == 7


def test_display_streak_solved_yesterday_is_still_alive():
    state = StreakState(current=7, longest=7, last_solved=YESTERDAY)
    assert displayed_streak(state, TODAY) == 7


def test_display_streak_broken_shows_zero():
    state = StreakState(current=7, longest=7, last_solved=LAST_WEEK)
    assert displayed_streak(state, TODAY) == 0


def test_display_streak_never_solved():
    state = StreakState(current=0, longest=0, last_solved=None)
    assert displayed_streak(state, TODAY) == 0
