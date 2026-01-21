from altrepo_api.api.errata.endpoints.search import FindErratas


class _NoDbConnection:
    request_line = ""

    def send_request(self, **kwargs):
        raise AssertionError("DB access is not expected when type='exclusion'")

    def drop_connection(self):
        return None


def test_find_erratas_exclusion_uses_sa_results(monkeypatch):
    sample_erratas = [
        {
            "errata_id": "ALT-SA-2024-0001-1",
            "eh_type": "exclusion",
            "task_id": 1,
            "branch": "sisyphus",
            "pkgs": [],
            "vuln_ids": [],
            "vuln_types": [],
            "changed": "2024-01-02T00:00:00+00:00",
            "is_discarded": False,
            "vulnerabilities": [{"id": "CVE-2024-0001", "type": "vuln"}],
            "packages": [{"pkg_name": "pkg1"}],
            "json": {},
        },
        {
            "errata_id": "ALT-SA-2023-0001-1",
            "eh_type": "exclusion",
            "task_id": 2,
            "branch": "sisyphus",
            "pkgs": [],
            "vuln_ids": [],
            "vuln_types": [],
            "changed": "2024-01-01T00:00:00+00:00",
            "is_discarded": False,
            "vulnerabilities": [{"id": "CVE-2023-0001", "type": "vuln"}],
            "packages": [{"pkg_name": "pkg2"}],
            "json": {},
        },
    ]

    monkeypatch.setattr(FindErratas, "_get_sa_erratas", lambda self: sample_erratas)

    worker = FindErratas(
        _NoDbConnection(),
        type="exclusion",
        page=1,
        limit=10,
        public_only=True,
    )

    result, code, headers = worker.get()

    assert code == 200
    assert headers["X-Total-Count"] == len(sample_erratas)
    returned_ids = [err["errata_id"] for err in result["erratas"]]
    # sorted by changed desc
    assert returned_ids == ["ALT-SA-2024-0001-1", "ALT-SA-2023-0001-1"]
    assert all(err["eh_type"] == "exclusion" for err in result["erratas"])
