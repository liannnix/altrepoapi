import pytest

from altrepo_api.libs.librpm_functions import (
    compare_versions,
    check_dependency_overlap,
    Dependency,
)


def _repack_version_kwargs(kwargs: dict, suffix: str) -> dict:
    return {(k + suffix): v for k, v in kwargs.items()}


@pytest.mark.parametrize(
    "version1,version2,expected",
    [
        (
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            0,
        ),
        (
            {"version": "6.04.pre3", "release": "alt2"},
            {"version": "6.04.pre3", "release": "alt2"},
            0,
        ),
        (
            {"epoch": 1, "version": "5.04", "release": "alt2"},
            {"version": "6.04.pre3", "release": "alt2"},
            1,
        ),
        (
            {"epoch": 0, "version": "5.04.pre3", "release": "alt2"},
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            -1,
        ),
        (
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            {"epoch": 0, "version": "6.04.pre3", "release": "alt1"},
            1,
        ),
        (
            {"epoch": 1, "version": "6.04.pre3", "release": "alt2"},
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            1,
        ),
        (
            {"epoch": 0, "version": "6.04.pre3", "release": "alt2"},
            {"epoch": 1, "version": "6.04.pre3", "release": "alt2"},
            -1,
        ),
        (
            {
                "version": "6.04.pre3",
                "release": "alt2",
                "disttag": "sisyphus+284514.100.1.1",
            },
            {"version": "6.04.pre3", "release": "alt2"},
            1,
        ),
        (
            {"version": "6.04.pre3", "release": "alt2"},
            {"version": "6.04.pre3", "release": "alt2", "disttag": "p9+299000.100.1.1"},
            -1,
        ),
        (
            {
                "version": "6.04.pre3",
                "release": "alt2",
                "disttag": "sisyphus+284514.100.1.1",
            },
            {
                "version": "6.04.pre3",
                "release": "alt2",
                "disttag": "p10+288000.100.1.1",
            },
            1,
        ),
    ],
)
def test_compare_versions(version1, version2, expected):
    assert (
        compare_versions(
            **_repack_version_kwargs(version1, "1"),
            **_repack_version_kwargs(version2, "2")
        )
        == expected
    )


DP_FLAG_NONE = 0
DP_FLAG_LESS = 0x02
DP_FLAG_EQUAL = 0x08
DP_FLAG_GREATER = 0x04
DP_FLAG_LESS_OR_EQUAL = DP_FLAG_LESS + DP_FLAG_EQUAL
DP_FLAG_GREATER_OR_EQUAL = DP_FLAG_GREATER + DP_FLAG_EQUAL


@pytest.mark.parametrize(
    "provide,require,expected",
    [
        (
            Dependency("test", "0", DP_FLAG_NONE),
            Dependency("test", "0", DP_FLAG_NONE),
            True,
        ),
        (
            Dependency("test", "0", DP_FLAG_NONE),
            Dependency("test", "set:fd6Z5n0", DP_FLAG_EQUAL),
            False,
        ),
        (
            Dependency("test", "set:fd6Z5n0", DP_FLAG_NONE),
            Dependency("test", "set:fd6Z5n0", DP_FLAG_EQUAL),
            True,
        ),
        (
            Dependency("test", "1.2.3", DP_FLAG_NONE),
            Dependency("test", "1.0.0", DP_FLAG_LESS),
            False,
        ),
        (
            Dependency("test", "1.2.3", DP_FLAG_NONE),
            Dependency("test", "1.0.0", DP_FLAG_LESS_OR_EQUAL),
            False,
        ),
        (
            Dependency("test", "1.2.3", DP_FLAG_NONE),
            Dependency("test", "1.0.0", DP_FLAG_GREATER_OR_EQUAL),
            True,
        ),
        (
            Dependency("test", "1.0.0", DP_FLAG_NONE),
            Dependency("test", "1.1.0", DP_FLAG_LESS),
            True,
        ),
        (
            Dependency("test", "1.0.0", DP_FLAG_NONE),
            Dependency("test", "1.1.0", DP_FLAG_LESS_OR_EQUAL),
            True,
        ),
        (
            Dependency("test", "1.0.0", DP_FLAG_NONE),
            Dependency("test", "1.1.0", DP_FLAG_GREATER),
            False,
        ),
        (
            Dependency("test", "1.0.0", DP_FLAG_NONE),
            Dependency("test", "1.1.0", DP_FLAG_GREATER_OR_EQUAL),
            False,
        ),
    ],
)
def test_check_dependency_overlap(provide, require, expected):
    assert check_dependency_overlap(*provide, *require) == expected
