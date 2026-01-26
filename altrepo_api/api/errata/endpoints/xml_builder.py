# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import xml.etree.ElementTree as xml

from alt_releases_matrix import OvalXml
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Iterable, Literal, NamedTuple, Union

from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import (
    VulnerabilityInfo as VulnInfo,
    parse_vulnerability_details,
)
from altrepo_api.libs.oval.altlinux_errata import (
    ALTLinuxAdvisory,
    Bugzilla,
    Severity,
    Vulnerability,
)
from altrepo_api.libs.oval.linux_definitions import (
    RPMInfoObject,
    RPMInfoState,
    RPMInfoTest,
    # RPMVerifyFileObject,
    # RPMVerifyFileState,
    # RPMVerifyFileTest,
    # RPMVerifyPackageObject,
    # RPMVerifyPackageState,
    # RPMVerifyPackageTest,
)
from altrepo_api.libs.oval.oval_definitions.type import (
    AffectedType,
    CriteriaType,
    CriterionType,
    OvalDefinitions,
    MetadataType,
    GeneratorType,
    DefinitionType,
    DefinitionsType,
    ObjectRefType,
    ObjectsType,
    ObjectType,
    ReferenceType,
    StateRefType,
    StatesType,
    StateType,
    TestsType,
    TestType,
)
from altrepo_api.libs.oval.oval_definitions.enumeration import (
    CheckEnumeration,
    ClassEnumeration,
    FamilyEnumeration,
    OperatorEnumeration,
    OperationEnumeration,
    # SimpleDatatypeEnumeration,
)
from altrepo_api.libs.oval.oval_definitions.entity import (
    EntityObjectIntType,
    EntityObjectStringType,
    # EntityObjectAnySimpleType,
    # EntityStateIntType,
    # EntityStateStringType,
    EntityStateAnySimpleType,
    EntityStateEVRStringType,
)
from altrepo_api.libs.oval.independent_definitions import (
    Textfilecontent54Object,
    Textfilecontent54State,
    Textfilecontent54Test,
)
from .common import ErrataID, BDU_ID_TYPE, BDU_ID_PREFIX, CVE_ID_TYPE, CVE_ID_PREFIX


_ovalxml = OvalXml()

LINK_BDU_BY_CVE = False

GENERATOR_PRODUCT_NAME = _ovalxml.generator_product_name
ALT_LINUX_OVAL_ID_PREFIX = _ovalxml.oval_id_prefix
XML_VERSION = _ovalxml.xml_version
ERRATA_BASE_URL = lut.errata_base
NVD_CVE_BASE_URL = lut.nvd_cve_base
FSTEC_BDU_BASE_URL = lut.fstec_bdu_base

PRODUCTS = {
    "p9": _ovalxml.p9_products,
    "p10": _ovalxml.p10_products,
    "p11": _ovalxml.p11_products,
    "c9f2": _ovalxml.c9f2_products,
    "c10f1": _ovalxml.c10f1_products,
    "c10f2": _ovalxml.c10f2_products,
}
PRODUCT_CPE = {
    "p9": _ovalxml.p9_cpes,
    "p10": _ovalxml.p10_cpes,
    "p11": _ovalxml.p11_cpes,
    "c9f2": _ovalxml.c9f2_cpes,
    "c10f1": _ovalxml.c10f1_cpes,
    "c10f2": _ovalxml.c10f2_cpes,
}
_regex_match_map = {
    k: v for k, v in zip(_ovalxml.cpe_regex_match_keys, _ovalxml.cpe_regex_match_values)
}
BRANCH_CHECK_REGEX = {
    k: (r, _regex_match_map[k])
    for k, r in zip(_ovalxml.cpe_regex_keys, _ovalxml.cpe_regex_values)
}
NUM_TO_SEVERITY = {0: "NONE", 1: "LOW", 2: "MEDUM", 3: "HIGH", 4: "CRITICAL"}
SEVERITY_TO_NUM = {v: k for k, v in NUM_TO_SEVERITY.items()}

EXPORT_BRANCHES = _ovalxml.export_branches
EXPORT_BRANCHES_MAP = {
    k: v for k, v in zip(_ovalxml.branches_map_keys, _ovalxml.branches_map_values)
}

logger = logging.getLogger(__name__)


class ErrataHistoryRecord(NamedTuple):
    errata_id: ErrataID
    eh_created: datetime
    eh_updated: datetime
    eh_hash: int
    eh_type: Literal["task", "branch", "bulletin"]
    eh_source: Literal["branch", "changelog"]
    eh_references_type: list[str]
    eh_references_link: list[str]
    pkg_hash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    task_id: int
    subtask_id: int
    task_state: str


class PackageInfo(NamedTuple):
    hash: int
    name: str
    epoch: int
    version: str
    release: str
    srcrpm_hash: int


class BinaryPackage(NamedTuple):
    name: str
    epoch: int
    version: str
    release: str


class BugzillaInfo(NamedTuple):
    id: int = 0
    summary: str = ""


class VulnerabilityInfo(NamedTuple):
    id: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    modified: datetime = datetime.now()
    published: datetime = datetime.now()
    json: str = ""
    refs: list[str] = list()


@dataclass
class SeqIndex:
    objects: int
    states: int
    tests: int


@dataclass
class CriteriaStruct:
    errata: ErrataHistoryRecord
    indexes: SeqIndex
    criteria: CriteriaType
    objects: list[ObjectType]
    states: list[StateType]
    tests: list[TestType]


def make_xml_file_name(errata_id: ErrataID) -> str:
    return f"{errata_id.no_version}.xml"


def num_to_severity_enum(num: int) -> Severity:
    if num <= 0 or num > 4:
        return Severity.NONE
    if num == 1:
        return Severity.LOW
    elif num == 2:
        return Severity.MEDIUM
    elif num == 3:
        return Severity.HIGH
    else:
        return Severity.CRITICAL


def serial_from_errata_id(errata_id: ErrataID) -> str:
    return "".join([str(errata_id.year), str(errata_id.number)])


def vuln_id_to_sort_key(vuln: str) -> Union[tuple[int, int], str]:
    try:
        if vuln.startswith(BDU_ID_PREFIX):
            s = vuln.lstrip(BDU_ID_PREFIX).split(":")[0]
            return (int(s.split("-")[1]), int(s.split("-")[2]))
        elif vuln.startswith(CVE_ID_PREFIX):
            s = vuln.lstrip(CVE_ID_PREFIX).split(":")[0]
            return (int(s.split("-")[1]), int(s.split("-")[2]))
        else:
            return vuln
    except (TypeError, ValueError, IndexError):
        logger.debug(f"Failed to parse `{vuln}` for sort key tuple")
        return vuln


def oval_id(type: Literal["def", "obj", "tst", "ste"], serial: str, index: int = 0):
    oval_id = f"oval:{ALT_LINUX_OVAL_ID_PREFIX}:{type}:{serial}"
    if index:
        oval_id += "{:03d}".format(index)
    return oval_id


def build_test_altlinux_distr_installed(
    branch: str,
) -> tuple[TestType, ObjectType, StateType]:
    # ALT linux distribution branch test is always the fisrt one
    seq = 1
    # ID's prefix is defined with `export_branches` mapping
    serial = EXPORT_BRANCHES_MAP.get(branch, "999")

    cpe_version_pattern, version_value = BRANCH_CHECK_REGEX[branch]

    object = Textfilecontent54Object(
        id=oval_id("obj", serial, seq),
        version=XML_VERSION,
        filepath=None,
        path=EntityObjectStringType("path", value="/etc"),
        filename=EntityObjectStringType("filepath", value="os-release"),
        pattern=EntityObjectStringType("pattern", value=cpe_version_pattern),
        instance=EntityObjectIntType("instance", value="1"),
        comment="Evaluate `/etc/os-release` file content",
    )
    object.pattern.attributes.operation = OperationEnumeration.pattern_match

    state = Textfilecontent54State(
        id=oval_id("ste", serial, seq),
        version=XML_VERSION,
        comment="verify distribution branch",
        subexpression=EntityStateAnySimpleType(
            "subexpression", value=version_value, datatype=None, entity_check=None
        ),
    )
    state.subexpression.attributes.operation = OperationEnumeration.equals  # type: ignore

    test = Textfilecontent54Test(
        id=oval_id("tst", serial, seq),
        version=XML_VERSION,
        check=CheckEnumeration.all,
        comment=f"ALT Linux based on branch '{branch}' must be installed",
        object=ObjectRefType(object.id),
        states=[
            StateRefType(state.id),
        ],
    )

    return (test, object, state)


def collect_uniq_binaries(packages: list[PackageInfo]) -> list[BinaryPackage]:
    uniq = set()

    for pkg in packages:
        bin_pkg = BinaryPackage(
            name=pkg.name,
            epoch=pkg.epoch,
            version=pkg.version,
            release=pkg.release,
        )
        uniq.add(bin_pkg)

    return sorted(uniq, key=lambda x: x.name)


def _build_vuln_from_cve(vuln: VulnerabilityInfo) -> Vulnerability:
    cwe = ""
    cvss = ""
    cvss3 = ""
    href = vuln.url
    impact = num_to_severity_enum(
        SEVERITY_TO_NUM.get(vuln.severity.upper(), SEVERITY_TO_NUM["LOW"])
    )

    # parse CVE contents using implementation from `api.vulnerabilities.common`
    vuln_json: dict[str, Any] = {}
    try:
        vuln_json = json.loads(vuln.json)
    except Exception:
        logger.debug(f"Failed to parse vulnerability JSON for {vuln.id}")
    else:
        if parsed := parse_vulnerability_details(
            VulnInfo(
                id=vuln.id,
                summary=vuln.summary,
                score=vuln.score,
                severity=vuln.severity,
                url=vuln.url,
                modified=vuln.modified,
                published=vuln.published,
                json=vuln_json,
                refs_type=[],
                refs_link=[],
            )
        ):
            # get CWE
            if parsed.cwes:
                cwe = ", ".join(parsed.cwes)
            # get CVSS V2.0
            for vec in parsed.cvss_vectors:
                if vec.version == "2.0":
                    cvss = vec.vector
            #  get CVSS V3.x
            for vec in parsed.cvss_vectors:
                if vec.version == "3.x":
                    cvss3 = vec.vector

    return Vulnerability(
        id=vuln.id,
        cvss=cvss,
        cvss3=cvss3,
        href=href,
        impact=impact,  # type: ignore
        cwe=cwe,
        public=vuln.published,
    )


def _build_vuln_from_bdu(vuln: VulnerabilityInfo) -> Vulnerability:
    cwe = ""
    cvss = ""
    cvss3 = ""
    href = vuln.url
    impact = num_to_severity_enum(
        SEVERITY_TO_NUM.get(vuln.severity.upper(), SEVERITY_TO_NUM["LOW"])
    )

    # parse BDU contents using implementation from `api.vulnerabilities.common`
    vuln_json: dict[str, Any] = {}
    try:
        vuln_json = json.loads(vuln.json)
    except Exception:
        logger.debug(f"Failed to parse vulnerability JSON for {vuln.id}")
    else:
        if parsed := parse_vulnerability_details(
            VulnInfo(
                id=vuln.id,
                summary=vuln.summary,
                score=vuln.score,
                severity=vuln.severity,
                url=vuln.url,
                modified=vuln.modified,
                published=vuln.published,
                json=vuln_json,
                refs_type=[],
                refs_link=[],
            )
        ):
            # get CWE
            if parsed.cwes:
                cwe = ", ".join(parsed.cwes)
            # get CVSS V2.0
            for vec in parsed.cvss_vectors:
                if vec.version == "2.0":
                    cvss = vec.vector
            #  get CVSS V3.x
            for vec in parsed.cvss_vectors:
                if vec.version == "3.x":
                    cvss3 = vec.vector

    return Vulnerability(
        id=vuln.id,
        cvss=cvss,
        cvss3=cvss3,
        href=href,
        impact=impact,  # type: ignore
        cwe=cwe,
        public=vuln.published,
    )


def _build_vuln_from_other(vuln: VulnerabilityInfo) -> Vulnerability:
    return Vulnerability(
        id=vuln.id,
        href=vuln.url,
        public=vuln.published,
        impact=num_to_severity_enum(
            SEVERITY_TO_NUM.get(vuln.severity.upper(), SEVERITY_TO_NUM["LOW"])
        ),  # type: ignore
        cwe="",
        cvss="",
        cvss3="",
    )


class OVALBuilder:
    def __init__(
        self,
        erratas: list[ErrataHistoryRecord],
        binaries: dict[int, list[PackageInfo]],
        bugz: dict[int, BugzillaInfo],
        vulns: dict[str, VulnerabilityInfo],
        bdus_by_cves: dict[str, VulnerabilityInfo],
    ) -> None:
        self.erratas = erratas
        self.binaries = binaries
        self.bugz = bugz
        self.vulns = vulns
        self.bdus_by_cves = bdus_by_cves
        self.bdu_to_cve_map = {
            bdu.id: {r for r in bdu.refs if r.startswith(CVE_ID_PREFIX)}
            for bdu in self.bdus_by_cves.values()
        }

    def _errata_bug_links(self, errata: ErrataHistoryRecord) -> list[str]:
        return [
            rl
            for rt, rl in zip(errata.eh_references_type, errata.eh_references_link)
            if rt == lut.errata_ref_type_bug
        ]

    def _errata_vuln_links(
        self, errata: ErrataHistoryRecord, link_bdu_by_cve: bool = LINK_BDU_BY_CVE
    ) -> list[str]:
        # collect vulnerabilities descriptions and references
        errata_linked_vulns = {
            rl
            for rt, rl in zip(errata.eh_references_type, errata.eh_references_link)
            if rt == lut.errata_ref_type_vuln
        }

        if link_bdu_by_cve:
            # extend vulnerabilities list by BDUs mapped by CVEs
            linked_bdus: set[str] = set()
            for bdu_id, linked_cves in self.bdu_to_cve_map.items():
                for cve_id in (
                    c for c in errata_linked_vulns if c.startswith(CVE_ID_PREFIX)
                ):
                    if cve_id in linked_cves:
                        linked_bdus.add(bdu_id)
            errata_linked_vulns = errata_linked_vulns.union(linked_bdus)

        return list(errata_linked_vulns)

    def _get_vuln_info_by_id(self, link: str) -> Union[VulnerabilityInfo, None]:
        return self.vulns.get(link, self.bdus_by_cves.get(link, None))

    def _build_vendor(self, errata: ErrataHistoryRecord) -> ALTLinuxAdvisory:
        bugs_list: list[tuple[int, BugzillaInfo]] = []
        vulns_list: list[tuple[str, VulnerabilityInfo]] = []
        max_priority = SEVERITY_TO_NUM["LOW"]

        # collect bugs descriptions and references
        for link in self._errata_bug_links(errata):
            bug = self.bugz.get(int(link))
            if bug is not None:
                bugs_list.append((int(link), bug))

        # colect bugs objects
        bugs: list[Bugzilla] = []
        for bug in sorted(bugs_list, key=lambda x: x[0]):
            bugs.append(Bugzilla(id=bug[0], summary=bug[1].summary))

        # collect vulnerabilities descriptions and references
        for link in self._errata_vuln_links(errata):
            vuln = self._get_vuln_info_by_id(link)
            if vuln is not None:
                vulns_list.append((link, vuln))
                vuln_priority = SEVERITY_TO_NUM.get(vuln.severity.upper(), 0)
                if vuln_priority > max_priority:
                    max_priority = vuln_priority

        # colect vulnerabilities info objects
        _vulns: list[Vulnerability] = []
        for vuln_id, vuln in sorted(
            vulns_list,
            key=lambda x: vuln_id_to_sort_key(x[0]),
        ):
            if vuln_id.startswith(CVE_ID_PREFIX):
                _vulns.append(_build_vuln_from_cve(vuln))
            elif vuln_id.startswith(BDU_ID_PREFIX):
                _vulns.append(_build_vuln_from_bdu(vuln))
            else:
                _vulns.append(_build_vuln_from_other(vuln))

        # collect affected CPEs
        cpes = PRODUCT_CPE.get(errata.pkgset_name, [])

        # set advisory dates
        errata_created = errata.eh_created
        errata_updated = errata.eh_updated

        # build vendor advisory
        return ALTLinuxAdvisory(
            severity=num_to_severity_enum(max_priority),  # type: ignore
            issued=errata_created,
            updated=errata_updated,
            vuln=_vulns,
            bugzilla=bugs,
            affected_cpe_list=cpes,
        )

    def _build_meta(self, errata: ErrataHistoryRecord) -> MetadataType:
        fix_list = []
        bugs_list = []
        vulns_list = []
        references: list[ReferenceType] = []
        vuln_references: list[ReferenceType] = []

        references.append(
            ReferenceType(
                source="".join(errata.errata_id.id.split("-")[0:2]),
                ref_id=errata.errata_id.no_version,
                ref_url=f"{ERRATA_BASE_URL}/{errata.errata_id.no_version}",
            )
        )

        # collect bugs descriptions and references
        for link in self._errata_bug_links(errata):
            bug = self.bugz.get(int(link))
            if bug is not None:
                bugs_list.append(f"#{link}: {bug.summary}")
            else:
                logger.debug(f"Failed to get bug details for {link}")

        # build vulnerabilities references
        for link in self._errata_vuln_links(errata):
            vuln = self._get_vuln_info_by_id(link)
            if vuln is not None:
                vulns_list.append(f"{link}: {vuln.summary}")
                if vuln.id.startswith(CVE_ID_PREFIX):
                    vuln_references.append(
                        ReferenceType(
                            source=CVE_ID_TYPE, ref_id=vuln.id, ref_url=vuln.url
                        )
                    )
                elif link.startswith(BDU_ID_PREFIX):
                    vuln_references.append(
                        ReferenceType(
                            source=BDU_ID_TYPE, ref_id=vuln.id, ref_url=vuln.url
                        )
                    )
                else:
                    logger.warning(f"Failed to create reference for {link}")
            else:
                logger.debug(f"Failed to get vulnerability details for {link}")
                vulns_list.append(f"{link}: description unavailable")
                if link.startswith(CVE_ID_PREFIX):
                    vuln_references.append(
                        ReferenceType(
                            source=CVE_ID_TYPE,
                            ref_id=link,
                            ref_url=f"{NVD_CVE_BASE_URL}/{link}",
                        )
                    )
                elif link.startswith(BDU_ID_PREFIX):
                    vuln_references.append(
                        ReferenceType(
                            source=BDU_ID_TYPE,
                            ref_id=link,
                            ref_url=f"{FSTEC_BDU_BASE_URL}/{link.split(':')[-1]}",
                        )
                    )
                else:
                    logger.warning(f"Failed to create reference for {link}")

        references.extend(sorted(vuln_references, key=lambda x: x.ref_id))

        fix_list = "\n\n * ".join(
            sorted(vulns_list, key=lambda x: vuln_id_to_sort_key(x)) + sorted(bugs_list)
        )

        description = (
            f"This update upgrades {errata.pkg_name} to version {errata.pkg_version}-{errata.pkg_release}. "
            f"\nSecurity Fix(es):\n\n * {fix_list}"
        )

        return MetadataType(
            title=(
                f"{errata.errata_id.no_version}: package `{errata.pkg_name}` update "
                f"to version {errata.pkg_version}-{errata.pkg_release}"
            ),
            description=description,
            references=references,
            extension_point=self._build_vendor(errata),
            affected=[
                AffectedType(
                    family=FamilyEnumeration.unix,
                    platform=[
                        f"ALT Linux branch {errata.pkgset_name}",
                    ],
                    product=[p for p in PRODUCTS.get(errata.pkgset_name, [])],
                ),
            ],
        )

    def _process_binaries(self, struct: CriteriaStruct):
        serial = serial_from_errata_id(struct.errata.errata_id)

        #  create new criteria child object
        criteria = CriteriaType(operator=OperatorEnumeration.OR)
        criteria.criterions = []

        evr_state: dict[str, StateType] = {}

        for binary in collect_uniq_binaries(self.binaries[struct.errata.pkg_hash]):
            evr = f"{binary.epoch}:{binary.version}-{binary.release}"
            comment_obj = f"{binary.name} is installed"
            comment_ste = f"package EVR is earlier than {evr}"
            comment_tst = f"{binary.name} is earlier than {evr}"

            # build package object
            object = RPMInfoObject(
                id=oval_id("obj", serial, struct.indexes.objects),
                version=XML_VERSION,
                comment=comment_obj,
                name=EntityObjectStringType("name", value=binary.name),
            )
            struct.indexes.objects += 1
            struct.objects.append(object)

            # build state object
            if evr not in evr_state:
                state = RPMInfoState(
                    id=oval_id("ste", serial, struct.indexes.states),
                    version=XML_VERSION,
                    comment=comment_ste,
                    evr=EntityStateEVRStringType("evr", value=evr, entity_check=None),
                )
                state.evr.attributes.operation = OperationEnumeration.less_than  # type: ignore
                struct.indexes.states += 1
                struct.states.append(state)
                evr_state[evr] = state
            else:
                state = evr_state[evr]

            # build test object
            test = RPMInfoTest(
                id=oval_id("tst", serial, struct.indexes.tests),
                version=XML_VERSION,
                comment=comment_tst,
                check=CheckEnumeration.all,
                object=ObjectRefType(object.id),
                states=[StateRefType(state.id)],
            )
            struct.indexes.tests += 1
            struct.tests.append(test)

            # build criterion
            criteria.criterions.append(
                CriterionType(test_ref=test.id, comment=comment_tst)
            )

        #  add binaries tests criteria to root one
        struct.criteria.criterias = [criteria]

    def _build_criteria(
        self, errata: ErrataHistoryRecord
    ) -> tuple[CriteriaType, list[ObjectType], list[StateType], list[TestType]]:
        obj_seq = 1
        test_seq = 1
        state_seq = 1

        # need to create test, states and objects that matches
        # 1. Linux distribution installed with exact branch
        # 2. Binary packages (found by source package) installed in system
        # and version is less that specified
        # 3. build criteria that contains buid tests with proper logical relation operations

        # 1: Linux distribution installed with exact branch
        t, o, s = build_test_altlinux_distr_installed(errata.pkgset_name)

        objects: list[ObjectType] = [o]
        states: list[StateType] = [s]
        tests: list[TestType] = [t]

        criteria = CriteriaType(operator=OperatorEnumeration.AND)

        criteria.criterions = [
            CriterionType(test_ref=t.id, comment="ALT Linux must be installed"),
        ]

        # 2: build crieria for binary pakages
        self._process_binaries(
            struct=CriteriaStruct(
                errata=errata,
                indexes=SeqIndex(obj_seq, state_seq, test_seq),
                criteria=criteria,
                objects=objects,
                states=states,
                tests=tests,
            )
        )

        return criteria, objects, states, tests

    def _build_definition(
        self, errata: ErrataHistoryRecord
    ) -> tuple[DefinitionType, list[ObjectType], list[StateType], list[TestType]]:
        metadata = self._build_meta(errata)
        criteria, objects, states, tests = self._build_criteria(errata)

        defintion = DefinitionType(
            id=oval_id("def", serial_from_errata_id(errata.errata_id)),
            version=XML_VERSION,
            class_=ClassEnumeration.patch,
            metadata=metadata,
            criteria=criteria,
        )

        return defintion, objects, states, tests

    def build_one_xml(
        self,
        timestamp: datetime,
        definitions: list[DefinitionType],
        objects: list[ObjectType],
        states: list[StateType],
        tests: list[TestType],
    ) -> BytesIO:
        xml_file = BytesIO()

        root = OvalDefinitions(
            generator=GeneratorType(
                timestamp=timestamp,
                product_name=GENERATOR_PRODUCT_NAME,
            ),
            definitions=DefinitionsType(definitions),
            objects=ObjectsType(objects),
            states=StatesType(states),
            tests=TestsType(tests),
        )

        tree = xml.ElementTree(root.to_xml())
        tree.write(xml_file)

        return xml_file

    def build(self, one_file: bool = False) -> Iterable[tuple[str, BytesIO]]:
        if not one_file:
            for errata in self.erratas:
                xml_file_name = make_xml_file_name(errata.errata_id)
                definition, objects, states, tests = self._build_definition(errata)
                yield xml_file_name, self.build_one_xml(
                    timestamp=errata.eh_updated,
                    definitions=[definition],
                    objects=objects,
                    states=states,
                    tests=tests,
                )
        else:
            timestamp = datetime.now()
            xml_file = BytesIO()
            branch = ""
            first_definition = True

            definitions: list[DefinitionType] = []
            objects: list[ObjectType] = []
            states: list[StateType] = []
            tests: list[TestType] = []

            # make document root
            root = OvalDefinitions(
                generator=GeneratorType(
                    timestamp=timestamp,
                    product_name=GENERATOR_PRODUCT_NAME,
                ),
                definitions=None,
                objects=None,
                states=None,
                tests=None,
            )

            # collect contents from errata list
            for errata in self.erratas:
                _definition, _objects, _states, _tests = self._build_definition(errata)
                # collect common platform test criteria, test, state and object
                if first_definition:
                    branch = errata.pkgset_name
                    # collect data
                    (
                        platform_test,
                        platform_object,
                        platform_state,
                    ) = build_test_altlinux_distr_installed(branch=branch)
                    platform_criterion = CriterionType(
                        test_ref=platform_test.id,
                        comment="ALT Linux must be installed",
                    )
                    # append collested data
                    objects.append(platform_object)
                    states.append(platform_state)
                    tests.append(platform_test)

                    first_definition = False
                # replace common platform test criteria, test, state and object
                _definition.criteria.criterions = [platform_criterion]  # type: ignore
                # append errata current errata definitions, tests, objects and states
                definitions.append(_definition)
                objects.extend(_objects[1:])
                states.extend(_states[1:])
                tests.extend(_tests[1:])

            # update document root
            root.definitions = DefinitionsType(definitions)
            root.objects = ObjectsType(objects)
            root.states = StatesType(states)
            root.tests = TestsType(tests)

            tree = xml.ElementTree(root.to_xml())
            tree.write(xml_file)

            xml_file_name = "{branch}_{date}.xml".format(
                branch=branch, date=timestamp.strftime("%Y%m%d")
            )

            yield xml_file_name, xml_file
            return
