from altrepo_api.api.management.endpoints.vuln_status_select_next import (
    VulnStatusSelectNext,
)


class _DummyConnection:
    def __init__(self, response):
        self.response = response
        self.query = ""

    def send_request(self, query, **kwargs):
        self.query = query
        return True, self.response

    def drop_connection(self):
        return None


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.split())


def test_vuln_status_select_next_applies_sort_fields():
    conn = _DummyConnection([("CVE-1234-0001",)])
    worker = VulnStatusSelectNext(
        conn, args={"sort": ["-modified", "severity"], "current_vuln_id": None}
    )

    result, code = worker.get()

    assert code == 200
    assert result["vuln_id"] == "CVE-1234-0001"
    normalized_sql = _normalize_sql(conn.query)
    assert (
        "ORDER BY vuln_modified_date DESC, vuln_severity ASC, vuln_id DESC"
        in normalized_sql
    )


def test_vuln_status_select_next_defaults_to_id_sort():
    conn = _DummyConnection([("CVE-9999-0001",)])
    worker = VulnStatusSelectNext(conn, args={})

    worker.get()

    normalized_sql = _normalize_sql(conn.query)
    assert "ORDER BY vuln_id DESC" in normalized_sql
