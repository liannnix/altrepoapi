import json
import pytest
import datetime

from altrepo_api import utils


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("", 0),
        (b"", 0),
        ("test", 3922541806432070687),
        (b"\x12\x34\x56\x78\x90", 13880256006903042099),
    ],
)
def test_mmhash(test_input, expected):
    assert utils.mmhash(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            [
                "c7",
                "sisyphus",
                "p10",
                "p9_mipsel",
                "p10_e2k",
                "p8",
                "5.0",
                "sisyphus_riscv64",
            ],
            (
                "sisyphus",
                "sisyphus_riscv64",
                "p10",
                "p10_e2k",
                "p9_mipsel",
                "p8",
                "c7",
                "5.0",
            ),
        ),
    ],
)
def test_sort_branches(test_input, expected):
    assert utils.sort_branches(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            (
                ("elem1", "elem2", "elem3"),
                ("elem1.1", "elem2.1", "elem3.1"),
                ("elem1.2", "elem2.2", "elem3.2"),
            ),
            ("elem1", "elem1.1", "elem1.2"),
        )
    ],
)
def test_join_tuples(test_input, expected):
    assert utils.join_tuples(test_input) == expected


def test_convert_to_json():
    values = [
        ("elem1", "elem2", "elem3"),
        ("elem1.1", "elem2.1", "elem3.1"),
        ("elem1.2", "elem2.2", "elem3.2"),
    ]
    js = json.loads(utils.convert_to_json(["key1", "key2", "key3"], values))

    assert "elem1" == js["0"]["key1"]
    assert "elem2.1" == js["1"]["key2"]
    assert "elem3.2" == js["2"]["key3"]


def test_tuplelist_to_dict():
    assert {1: [2], 2: [3, 4], 7: [8, 9]} == utils.tuplelist_to_dict(
        [(1, 2), (2, 3, 4, 6), (7, 8, 9)], 2
    )
    assert {1: [2, 3, 4, 5], 6: [7, 8], 9: [0, 1, 2]} == utils.tuplelist_to_dict(
        [(1, 2, 3, 4, 5), (6, 7, 8), (9, 0, 1, 2)], 4
    )
    assert {1: [2, 3, 4], 3: []} == utils.tuplelist_to_dict(
        [(1,), (1, 2, 3, 4), (3,)], 6
    )


def test_datetime_to_iso():
    assert "2020-10-20T12:34:56" == utils.datetime_to_iso(
        datetime.datetime(2020, 10, 20, 12, 34, 56)
    )


@pytest.mark.skip("not covered by tests")
def test_get_nickname_from_packager():
    pass


@pytest.mark.skip("not covered by tests")
def test_dp_flags_decode():
    pass


@pytest.mark.skip("not covered by tests")
def test_full_file_permissions():
    pass
