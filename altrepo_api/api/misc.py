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

from dataclasses import dataclass

from alt_releases_matrix import (
    Beehive,
    BranchInheritance,
    Errata,
    Images,
    Repology,
    Vulnerability,
    BUGZILLA_BASE_URL,
    ERRATA_BASE_URL,
    GITALT_BASE_URL,
    GITALT_TASKS_BASE_URL,
    KNOW_BRANCHES,
    KNOWN_ARCHS,
    PACKAGES_BASE_URL,
    PUBLIC_FTP_BASE_URL,
)

_beehive = Beehive()
_branch_inheritance = BranchInheritance()
_errata = Errata()
_images = Images()
_repology = Repology()
_vuln = Vulnerability()


_repology_branch_map = {
    k: v for k, v in zip(_repology.branch_map_keys, _repology.branch_map_values)
}
_repology_reverse_branch_map: dict[str, list[str]] = {}
for key, value in _repology_branch_map.items():
        _repology_reverse_branch_map.setdefault(value, []).append(key)

@dataclass(frozen=True)
class LookupTables:
    known_branches = KNOW_BRANCHES
    taskless_branches = [
        "p9_mipsel",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "sisyphus_loongarch64",
        "sisyphus_e2k",
        "p9_e2k",
        "p10_e2k",
    ]

    no_downloads_branches = ["sisyphus_e2k", "p9_e2k", "p10_e2k"]

    repology_branches = _repology.branches
    repology_export_branches = _repology.export_branches
    repology_branch_map = _repology_branch_map
    repology_reverse_branch_map= _repology_reverse_branch_map

    known_archs = KNOWN_ARCHS
    known_repo_components = [
        "debuginfo",
        "classic",
        "srpm",
        "checkinstall",
        "gostcrypto",
    ]
    default_archs = ["x86_64", "i586", "aarch64", "armh", "ppc64le", "noarch"]
    branch_wds_default_archs = {
        # RISCV64
        "sisyphus_riscv64": ["noarch", "riscv64"],
        # MIPSEL
        "sisyphus_mipsel": ["noarch", "mipsel"],
        "p9_mipsel": ["noarch", "mipsel"],
        # E2K
        "sisyphus_e2k": ["noarch", "e2k", "e2kv4", "e2kv5", "e2kv6"],
        "p10_e2k": ["noarch", "e2k", "e2kv4", "e2kv5", "e2kv6"],
        "p9_e2k": ["noarch", "e2k", "e2kv4", "e2kv5", "e2kv6"],
        # LOONGARCH
        "sisyphus_loongarch64": ["noarch", "loongarch64"],
        # MAIN
        "default": ["noarch", "x86_64"],
    }
    package_params = [
        "pkg_cs",
        "pkg_packager",
        "pkg_packager_email",
        "pkg_name",
        "pkg_arch",
        "pkg_version",
        "pkg_release",
        "pkg_epoch",
        "pkg_serial_",
        "pkg_buildtime",
        "pkg_buildhost",
        "pkg_size",
        "pkg_archivesize",
        "pkg_rpmversion",
        "pkg_cookie",
        "pkg_disttag",
        "pkg_sourcerpm",
        "pkg_filename",
        "pkg_filesize",
        "pkg_srcrpm_hash",
        "pkg_summary",
        "pkg_description",
        "pkg_distribution",
        "pkg_vendor",
        "pkg_gif",
        "pkg_xpm",
        "pkg_license",
        "pkg_group_",
        "pkg_url",
        "pkg_os",
        "pkg_prein",
        "pkg_postin",
        "pkg_preun",
        "pkg_postun",
        "pkg_icon",
        "pkg_preinprog",
        "pkg_postinprog",
        "pkg_preunprog",
        "pkg_postunprog",
        "pkg_buildarchs",
        "pkg_verifyscript",
        "pkg_verifyscriptprog",
        "pkg_prefixes",
        "pkg_instprefixes",
        "pkg_optflags",
        "pkg_disturl",
        "pkg_payloadformat",
        "pkg_payloadcompressor",
        "pkg_payloadflags",
        "pkg_platform",
        "pkg_sourcepackage",
    ]
    pkg_groups = [
        "Accessibility",
        "Archiving/Backup",
        "Archiving/Cd burning",
        "Archiving/Compression",
        "Archiving/Other",
        "Books/Computer books",
        "Books/Faqs",
        "Books/Howtos",
        "Books/Other",
        "Communications",
        "Databases",
        "Development/C",
        "Development/C++",
        "Development/Databases",
        "Development/Debug",
        "Development/Debuggers",
        "Development/Documentation",
        "Development/Erlang",
        "Development/Functional",
        "Development/GNOME and GTK+",
        "Development/Haskell",
        "Development/Java",
        "Development/KDE and QT",
        "Development/Kernel",
        "Development/Lisp",
        "Development/ML",
        "Development/Objective-C",
        "Development/Other",
        "Development/Perl",
        "Development/Python",
        "Development/Python3",
        "Development/Ruby",
        "Development/Scheme",
        "Development/Tcl",
        "Development/Tools",
        "Documentation",
        "Editors",
        "Education",
        "Emulators",
        "Engineering",
        "File tools",
        "Games/Adventure",
        "Games/Arcade",
        "Games/Boards",
        "Games/Cards",
        "Games/Educational",
        "Games/Other",
        "Games/Puzzles",
        "Games/Sports",
        "Games/Strategy",
        "Graphical desktop/Enlightenment",
        "Graphical desktop/FVWM based",
        "Graphical desktop/GNOME",
        "Graphical desktop/GNUstep",
        "Graphical desktop/Icewm",
        "Graphical desktop/KDE",
        "Graphical desktop/MATE",
        "Graphical desktop/Motif",
        "Graphical desktop/Other",
        "Graphical desktop/Sawfish",
        "Graphical desktop/Sugar",
        "Graphical desktop/Window Maker",
        "Graphical desktop/XFce",
        "Graphics",
        "Monitoring",
        "Networking/Chat",
        "Networking/DNS",
        "Networking/FTN",
        "Networking/File transfer",
        "Networking/IRC",
        "Networking/Instant messaging",
        "Networking/Mail",
        "Networking/News",
        "Networking/Other",
        "Networking/Remote access",
        "Networking/WWW",
        "Office",
        "Other",
        "Publishing",
        "Sciences/Astronomy",
        "Sciences/Biology",
        "Sciences/Chemistry",
        "Sciences/Computer science",
        "Sciences/Geosciences",
        "Sciences/Mathematics",
        "Sciences/Medicine",
        "Sciences/Other",
        "Sciences/Physics",
        "Security/Antivirus",
        "Security/Networking",
        "Shells",
        "Sound",
        "System/Base",
        "System/Configuration/Boot and Init",
        "System/Configuration/Hardware",
        "System/Configuration/Networking",
        "System/Configuration/Other",
        "System/Configuration/Packaging",
        "System/Configuration/Printing",
        "System/Fonts/Console",
        "System/Fonts/True type",
        "System/Fonts/Type1",
        "System/Fonts/X11 bitmap",
        "System/Internationalization",
        "System/Kernel and hardware",
        "System/Legacy libraries",
        "System/Libraries",
        "System/Servers",
        "System/Servers/ZProducts",
        "System/X11",
        "System/XFree86",
        "Terminals",
        "Text tools",
        "Toys",
        "Video",
    ]
    known_beehive_branches = _beehive.branches
    known_beehive_archs = _beehive.archs

    known_image_components = _images.components
    known_image_platform = _images.platforms
    known_image_editions = _images.editions
    known_image_archs = _images.archs
    known_image_types = _images.types
    known_image_releases = _images.releases
    known_image_variants = _images.variants

    gitalt_base = GITALT_BASE_URL
    beehive_base = _beehive.base_url
    gitalt_tasks_base = GITALT_TASKS_BASE_URL
    packages_base = PACKAGES_BASE_URL
    bugzilla_base = BUGZILLA_BASE_URL
    public_ftp_base = PUBLIC_FTP_BASE_URL
    errata_base = ERRATA_BASE_URL
    nvd_cve_base = "https://nvd.nist.gov/vuln/detail"
    fstec_bdu_base = "https://bdu.fstec.ru/vul"
    ghsa_base = "https://github.com/advisories"
    mfsa_base = "https://www.mozilla.org/en-US/security/advisories"

    rpmsense_flags = [
        "RPMSENSE_ANY",
        "RPMSENSE_SERIAL",
        "RPMSENSE_LESS",
        "RPMSENSE_GREATER",
        "RPMSENSE_EQUAL",
        "RPMSENSE_PROVIDES",
        "RPMSENSE_CONFLICTS",
        "RPMSENSE_PREREQ",
        "RPMSENSE_OBSOLETES",
        "RPMSENSE_INTERP",
        "RPMSENSE_SCRIPT_PRE",
        "RPMSENSE_SCRIPT_POST",
        "RPMSENSE_SCRIPT_PREUN",
        "RPMSENSE_SCRIPT_POSTUN",
        "RPMSENSE_SCRIPT_VERIFY",
        "RPMSENSE_FIND_REQUIRES",
        "RPMSENSE_FIND_PROVIDES",
        "RPMSENSE_TRIGGERIN",
        "RPMSENSE_TRIGGERUN",
        "RPMSENSE_TRIGGERPOSTUN",
        "___SENSE_MULTILIB",
        "RPMSENSE_SCRIPT_PREP",
        "RPMSENSE_SCRIPT_BUILD",
        "RPMSENSE_SCRIPT_INSTALL",
        "RPMSENSE_SCRIPT_CLEAN",
        "RPMSENSE_RPMLIB",
        "RPMSENSE_TRIGGERPREIN",
        "RPMSENSE_KEYRING",
    ]

    known_states = [
        "FAILED",
        "EPERM",
        "DONE",
        "NEW",
        "DELETED",
        "TESTED",
        "AWAITING",
        "BUILDING",
        "PENDING",
        "FAILING",
        "POSTPONED",
        "COMMITTING",
        "SWEPT",
        "FAILURE",
    ]

    known_approvers = {
        "p11": ["@maint", "@tester"],
        "p10": ["@maint", "@tester"],
        "p9": ["@maint", "@tester"],
        "p8": ["snowmix", "amakeenk", "jenya"],
        "c10f2": ["@maint", "@tester"],
        "c10f1": ["@maint", "@tester"],
        "c9f2": ["@maint", "@tester"],
        "c9f1": ["@maint", "@tester"],
    }

    branch_tree_branches = [
        "sisyphus",
        "p11",
        "p10",
        "p9",
        "p8",
        "p7",
        "c10f2",
        "c10f1",
        "c9f2",
        "c9f1",
        "c8.1",
        "c8",
        "c7.1",
        "c7",
    ]

    branch_inheritance = {
        "c10f2": _branch_inheritance.c10f2,
        "c10f1": _branch_inheritance.c10f1,
        "c9f2": _branch_inheritance.c9f2,
        "c9f1": _branch_inheritance.c9f1,
        # "c8.1": ["c8", "p8", "sisyphus"],
        # "c8": ["p8", "sisyphus"],
        # "c7.1": ["c7", "p7", "sisyphus"],
        # "c7": ["p7", "sisyphus"],
        "p11": _branch_inheritance.p11,
        "p10": _branch_inheritance.p10,
        "p9": _branch_inheritance.p9,
        # "p8": ["sisyphus"],
        # "p7": ["sisyphus"],
        "sisyphus": _branch_inheritance.sisyphus,
    }
    branch_inheritance_root = _branch_inheritance.root

    known_errata_type = {"packages": ["branch", "task"], "repository": ["bulletin"]}

    errata_branch_update_prefix = _errata.branch_update_prefix
    errata_package_update_prefix = _errata.package_update_prefix
    errata_change_prefix = _errata.errata_change_prefix
    errata_advisory_prefix = _errata.security_advisory_prefix

    errata_ref_type_bug = _errata.reference_type_bug
    errata_ref_type_vuln = _errata.reference_type_vulnerability
    errata_ref_type_branch = _errata.reference_type_branch
    errata_ref_type_errata = _errata.reference_type_errata
    errata_ref_type_package = _errata.reference_type_package

    errata_manage_branches_with_tasks = (
        "c9f1",
        "c9f2",
        "c10f1",
        "c10f2",
        "p9",
        "p10",
        "p11",
        "sisyphus",
    )
    errata_manage_branches_without_tasks = (
        "p9_mipsel",
        "p9_e2k",
        "p10_e2k",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "sisyphus_e2k",
    )

    av_supported_branches = ("p10", "p11", "c9f2", "c10f1")
    av_known_scanners = ("drweb", "kesl")

    comment_ref_type_errata = _errata.reference_type_errata
    comment_ref_type_task = _errata.reference_type_task
    comment_ref_type_web = _errata.reference_type_web
    comment_ref_type_package = _errata.reference_type_package

    comment_ref_types = (
        errata_ref_type_bug,
        errata_ref_type_vuln,
        comment_ref_type_errata,
        comment_ref_type_task,
        comment_ref_type_web,
        comment_ref_type_package,
    )

    TYPE_COMMENT = "comment"
    TYPE_CPE = "cpe"
    TYPE_ERRATA = "errata"
    TYPE_EXCLUSION = "exclusion"
    TYPE_PNC = "pnc"
    TYPE_VULN_STATUS = "vuln_status"

    default_reason_source_type_exclusion = TYPE_EXCLUSION
    default_reason_source_type_cpe = TYPE_CPE
    default_reason_source_type_comment = TYPE_COMMENT
    default_reason_source_type_pnc = TYPE_PNC
    default_reason_source_type_vuln_status = TYPE_VULN_STATUS

    default_reason_source_types = (
        errata_ref_type_vuln,
        comment_ref_type_errata,
        comment_ref_type_task,
        default_reason_source_type_pnc,
        default_reason_source_type_cpe,
        default_reason_source_type_exclusion,
        default_reason_source_type_comment,
        default_reason_source_type_vuln_status,
    )

    vuln_status_new = "new"
    vuln_status_analyzing = "analyzing"
    vuln_status_working = "working"
    vuln_status_resolved = "resolved"

    vuln_status_statuses = (
        vuln_status_new,
        vuln_status_analyzing,
        vuln_status_working,
        vuln_status_resolved,
    )
    vuln_status_resolutions = ("not_for_us", "not_affected", "wont_fix", "our")
    vuln_status_json_fields = ("note", "project_name", "cpes")

    errata_user_last_activities_types = (
        TYPE_VULN_STATUS,
        TYPE_COMMENT,
        TYPE_ERRATA,
        TYPE_EXCLUSION,
        TYPE_CPE,
        TYPE_PNC,
    )

    vuln_types = (_vuln.cve_id_type, _vuln.bdu_id_type, _vuln.ghsa_id_type)

    feature_pnc_multi_mapping = "PNC_MULTI_MAPPING"

    errata_user_subscription_types = (
        _errata.reference_type_vulnerability,
        _errata.reference_type_package,
        _errata.reference_type_errata,
    )

    errata_user_tracking_types = (
        *errata_user_last_activities_types,
        _errata.reference_type_vulnerability,
    )


lut = LookupTables()
