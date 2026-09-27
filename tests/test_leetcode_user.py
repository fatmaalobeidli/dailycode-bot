import pytest

from bot.services.leetcode import LeetCodeError, parse_user_exists


def test_existing_user():
    assert parse_user_exists({"data": {"matchedUser": {"username": "sunny"}}}) is True


def test_unknown_user():
    assert parse_user_exists({"data": {"matchedUser": None}}) is False


def test_broken_response_raises():
    with pytest.raises(LeetCodeError):
        parse_user_exists({})


def test_unknown_user_with_graphql_error_is_not_a_failure():
    data = {
        "data": {"matchedUser": None},
        "errors": [{"message": "That user does not exist."}],
    }
    assert parse_user_exists(data) is False
