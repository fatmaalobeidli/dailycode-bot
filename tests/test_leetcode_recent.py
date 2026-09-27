from datetime import datetime, timezone

import pytest

from bot.services.leetcode import LeetCodeError, parse_recent_accepted


def test_parse_valid_response():
    data = {
        "data": {
            "recentAcSubmissionList": [
                {"titleSlug": "two-sum", "timestamp": "1790553540"},
                {"titleSlug": "valid-parentheses", "timestamp": "1790467200"},
            ]
        }
    }
    subs = parse_recent_accepted(data)
    assert [s.slug for s in subs] == ["two-sum", "valid-parentheses"]
    assert subs[0].solved_at == datetime(2026, 9, 27, 23, 59, tzinfo=timezone.utc)
    assert subs[0].solved_at.tzinfo == timezone.utc


def test_parse_none_list_returns_empty():
    assert parse_recent_accepted({"data": {"recentAcSubmissionList": None}}) == []


def test_parse_broken_structure_raises():
    with pytest.raises(LeetCodeError):
        parse_recent_accepted({"data": {}})


def test_parse_invalid_timestamp_raises():
    data = {
        "data": {"recentAcSubmissionList": [{"titleSlug": "x", "timestamp": "abc"}]}
    }
    with pytest.raises(LeetCodeError):
        parse_recent_accepted(data)
