import unittest

from altrepo_api.settings import namespace as settings

settings.LOG_TO_FILE = False  # type: ignore
settings.LOG_TO_SYSLOG = False

from altrepo_api.libs.conflict_filter import ConflictFilter


class TestConflictFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cf = ConflictFilter(None, False)  # type: ignore

    def test_get_conflicts(self):
        dA = {
            "conflict": [("syslinux", "", 0), ("syslinux4-extlinux", "", 0)],
            "provide": [
                ("exlinux", "6.04.pre3-alt2:sisyphus+240957.100.1.1", 8),
                ("syslinux4-exlinux", "6.04.pre3-alt2", 8),
            ],
        }
        dB = {
            "conflict": [],
            "provide": [("syslinux", "2:4.04-alt16:sisyphus+242564.100.1.1", 8)],
        }

        hshA, hshB = 17830059475705751619, 8505303502925891219

        assert [(17830059475705751619, 8505303502925891219)] == self.cf._get_conflicts(
            dA, dB, hshA, hshB
        )


if __name__ == "__main__":
    unittest.main()
