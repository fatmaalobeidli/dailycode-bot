import pytest

from bot.services.leetcode import LeetCodeError, parse_daily

SAMPLE = {
    "data": {
        "activeDailyCodingChallengeQuestion": {
            "date": "2026-09-27",
            "link": "/problems/two-sum/",
            "question": {
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
                "acRate": 55.1234,
                "topicTags": [{"name": "Array"}, {"name": "Hash Table"}],
            },
        }
    }
}


def test_parse_valid_response():
    p = parse_daily(SAMPLE)
    assert p.slug == "two-sum"
    assert p.url == "https://leetcode.com/problems/two-sum/"
    assert p.ac_rate == 55.1
    assert p.tags == ("Array", "Hash Table")


def test_parse_missing_daily_raises():
    with pytest.raises(LeetCodeError):
        parse_daily({"data": {"activeDailyCodingChallengeQuestion": None}})


def test_parse_broken_structure_raises():
    with pytest.raises(LeetCodeError):
        parse_daily({"data": {}})