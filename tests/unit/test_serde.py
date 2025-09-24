from datetime import datetime, UTC
from enum import Enum
from typing import NamedTuple, Optional
from uuid import UUID, uuid4


from altrepo_api.libs.errata_server.base import JSONValue
from altrepo_api.libs.errata_server.rusty import Ok
from altrepo_api.libs.errata_server.serde import (
    serialize,
    deserialize,
    serialize_enum,
    deserialize_enum,
)

UUID_V = uuid4()
UUID_S = str(UUID_V)
DT_V = datetime.now().astimezone(UTC)
DT_S = DT_V.isoformat()


class E(Enum):
    A = "a"
    B = "b"
    C = "c"

    def serialize(self) -> str:
        return serialize_enum(self)

    @staticmethod
    def deserialize(value: JSONValue):
        return deserialize_enum(E, value)


class NM(NamedTuple):
    i: int = 42
    s: str = "xxx"
    f: float = 1.0
    b: bool = True
    dt: datetime = DT_V
    uuid: UUID = UUID_V
    opt: Optional[UUID] = None
    e: E = E.A
    nested: Optional["NM"] = None


def test_enum_serialization():
    assert E.A.serialize() == "a"
    assert E.B.serialize() == "b"
    assert E.C.serialize() == "c"


def test_enum_deserialization():
    assert E.deserialize("a") == Ok(E.A)
    assert E.deserialize("b") == Ok(E.B)
    assert E.deserialize("c") == Ok(E.C)
    assert E.deserialize("d").is_err()


def test_named_tuple_simple_serialization():
    nm = NM(
        dt=DT_V,
        uuid=UUID_V,
    )
    assert serialize(nm) == {
        "i": 42,
        "s": "xxx",
        "f": 1.0,
        "b": True,
        "dt": DT_S,
        "uuid": UUID_S,
        "e": "a",
        "opt": None,
        "nested": None,
    }


def test_named_tuple_serialization_skip_nones():
    nm = NM()
    NM.SKIP_SERILIZING_IF_NONE = True  # type: ignore

    assert serialize(nm) == {
        "i": 42,
        "s": "xxx",
        "f": 1.0,
        "b": True,
        "dt": DT_S,
        "uuid": UUID_S,
        "e": "a",
    }


def test_named_tuple_serialization_enums():
    nm = NM(e=E.C)
    NM.SKIP_SERILIZING_IF_NONE = True  # type: ignore
    assert serialize(nm)["e"] == "c"


def test_named_tuple_serialization_optional():
    nm = NM(opt=UUID_V)
    assert serialize(nm)["opt"] == UUID_S

    nm = NM(opt=None)
    NM.SKIP_SERILIZING_IF_NONE = False  # type: ignore
    assert serialize(nm)["opt"] == None


def test_named_tuple_serialization_nested():
    nested = NM(e=E.B)
    nm = NM(nested=nested)
    NM.SKIP_SERILIZING_IF_NONE = True  # type: ignore

    assert serialize(nm).get("opt", "NA") == "NA"
    assert serialize(nm)["nested"].get("opt", "NA") == "NA"  # type: ignore
    assert serialize(nm)["nested"]["dt"] == DT_S  # type: ignore
    assert serialize(nm)["nested"]["e"] == "b"  # type: ignore


def test_named_tuple_deserialization_simple():
    json = {
        "i": 42,
        "s": "xxx",
        "f": 1.0,
        "b": True,
        "dt": DT_S,
        "uuid": UUID_S,
        "e": "a",
        "opt": None,
        "nested": None,
    }
    assert deserialize(NM, json) == Ok(
        NM(
            i=42,
            s="xxx",
            f=1.0,
            b=True,
            dt=DT_V,
            uuid=UUID_V,
            e=E.A,
        )
    )


def test_named_tuple_deserialization_defaults():
    json = {"s": "defaults", "opt": None}
    assert deserialize(NM, json) == Ok(
        NM(
            i=42,
            s="defaults",
            f=1.0,
            b=True,
            dt=DT_V,
            uuid=UUID_V,
            opt=None,
            e=E.A,
            nested=None,
        )
    )


def test_named_tuple_deserialization_optional():
    json = {
        "i": 42,
        "s": "xxx",
        "f": 1.0,
        "b": True,
        "dt": DT_S,
        "uuid": UUID_S,
        "e": "a",
        "opt": UUID_S,
        "nested": None,
    }
    assert deserialize(NM, json) == Ok(
        NM(
            i=42,
            s="xxx",
            f=1.0,
            b=True,
            dt=DT_V,
            uuid=UUID_V,
            e=E.A,
            opt=UUID_V,
        )
    )


def test_named_tuple_deserialization_nested():
    json = {
        "i": 42,
        "s": "xxx",
        "f": 1.0,
        "b": True,
        "dt": DT_S,
        "uuid": UUID_S,
        "e": "a",
        "opt": None,
        "nested": {
            "s": "nested 1",
            "opt": UUID_S,
            "nested": {
                "s": "nested 2",
            },
        },
    }
    assert deserialize(NM, json) == Ok(
        NM(
            dt=DT_V,
            uuid=UUID_V,
            nested=NM(
                s="nested 1",
                opt=UUID_V,
                nested=NM(
                    s="nested 2",
                ),
            ),
        )
    )
