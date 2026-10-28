from utils import timestamp

INPUT_TIMESTAMPS_1 = ["2023-12-24T20:59:09.5Z", "2023-12-24T20:58:57.748Z"]
INPUT_TIMESTAMPS_2 = ["2023-12-23T20:56:42.7Z", "2023-12-24T21:58:57.748Z"]
INPUT_TIMESTAMPS_3 = ["2023-12-25T20:56:42.7Z", "2023-12-24T21:58:57.748Z"]
INPUT_TIMESTAMPS_4 = ["2024-12-25T20:56:42.7Z", "2023-12-24T21:58:57.748Z"]
INPUT_TIMESTAMPS_5 = ["2024-01-25T20:56:42.7Z", "2023-12-24T21:58:57.748Z"]
INPUT_TIMESTAMPS_6 = ["2024-01-25T20:56:42.7Z", "2025-12-27T21:58:57.928Z", "2023-12-24T21:58:57.748Z"]


def test_get_timestamp_from_nvue():
    """NVUE oper-status-last-change must include date and time."""
    assert timestamp.get_timestamp_from_nvue("2026/07/28 01:05:29.254") == "2026-07-28T01:05:29.254Z"
    assert timestamp.get_timestamp_from_nvue("2026/07/28 01:05:29") == "2026-07-28T01:05:29.000Z"
    assert timestamp.get_timestamp_from_nvue(None) is None
    assert timestamp.get_timestamp_from_nvue("") is None
    assert timestamp.get_timestamp_from_nvue("2026/07/28") is None
    assert timestamp.get_timestamp_from_nvue("1722123456") is None
    assert timestamp.get_timestamp_from_nvue("never") is None
    assert timestamp.get_timestamp_from_nvue("Never") is None


def test_get_normalized_timestamp():
    """Sanity test for function standardize_timestamp"""
    assert timestamp.get_normalized_timestamp("2023-12-24T20:59:09.5Z") == "2023-12-24T20:59:09.500Z"
    assert timestamp.get_normalized_timestamp("2023-12-24T20:58:57.748Z") == "2023-12-24T20:58:57.748Z"
    assert timestamp.get_normalized_timestamp("2024-12-24T20:58:57.900Z") == "2024-12-24T20:58:57.900Z"


def test_most_recent_timestamp():
    """Sanity test for function most_recent_timestamp"""
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_1) == "2023-12-24T20:59:09.500Z"
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_2) == "2023-12-24T21:58:57.748Z"
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_3) == "2023-12-25T20:56:42.700Z"
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_4) == "2024-12-25T20:56:42.700Z"
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_5) == "2024-01-25T20:56:42.700Z"
    assert timestamp.most_recent_timestamp(INPUT_TIMESTAMPS_6) == "2025-12-27T21:58:57.928Z"


if __name__ == "__main__":
    test_get_timestamp_from_nvue()
    test_get_normalized_timestamp()
    test_most_recent_timestamp()
