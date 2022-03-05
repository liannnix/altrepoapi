import pytest

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
