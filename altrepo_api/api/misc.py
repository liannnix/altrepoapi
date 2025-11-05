# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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


@dataclass(frozen=True)
class LookupTables:
    known_branches = [
        "4.0",
        "4.1",
        "5.0",
        "5.1",
        "c6",
        "c7",
        "c7.1",
        "c8",
        "c8.1",
        "c9f1",
        "c9f2",
        "c10f1",
        "c10f2",
        "p5",
        "p6",
        "p7",
        "p8",
        "p9",
        "p9_mipsel",
        "p9_e2k",
        "p10",
        "p10_e2k",
        "p11",
        "sisyphus",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "sisyphus_e2k",
        "sisyphus_loongarch64",
        "t6",
        "t7",
        "icarus",
    ]
    taskless_branches = [
        "p9_mipsel",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "sisyphus_loongarch64",
        "sisyphus_e2k",
        "p9_e2k",
        "p10_e2k",
    ]
    oval_export_branches = ["p9", "p10", "p11", "c9f2", "c10f1", "c10f2"]
    oval_export_branches_map = {
        "p9": "1",
        "p10": "2",
        "p11": "3",
        "c9f2": "4",
        "c10f1": "5",
        "c10f2": "6",
    }
    no_downloads_branches = ["sisyphus_e2k", "p9_e2k", "p10_e2k"]

    repology_branches = ("altsisyphus", "alt_p9", "alt_p10", "alt_p11")
    repology_export_branches = ["sisyphus", "p9", "p10", "p11"]
    repology_branch_map = {
        # P9
        "p9": "alt_p9",
        "c9f1": "alt_p9",
        "c9f2": "alt_p9",
        "p9_e2k": "alt_p9",
        "p9_mipsel": "alt_p9",
        # P10
        "p10": "alt_p10",
        "c10f1": "alt_p10",
        "c10f2": "alt_p10",
        "p10_e2k": "alt_p10",
        # P11
        "p11": "alt_p11",
        # Sisyphus
        "sisyphus": "altsisyphus",
        "sisyphus_e2k": "altsisyphus",
        "sisyphus_mipsel": "altsisyphus",
        "sisyphus_riscv64": "altsisyphus",
        "sisyphus_loongarch64": "altsisyphus",
    }
    repology_reverse_branch_map = {
        # P9
        "alt_p9": ("p9", "c9f1", "c9f2", "p9_e2k", "p9_mipsel"),
        # P10
        "alt_p10": ("p10", "c10f1", "c10f2", "p10_e2k"),
        # P11
        "alt_p11": ("p11",),
        # Sisyphus
        "altsisyphus": (
            "sisyphus",
            "sisyphus_e2k",
            "sisyphus_mipsel",
            "sisyphus_riscv64",
            "sisyphus_loongarch64",
        ),
    }

    known_archs = [
        "noarch",
        "i586",
        "x86_64",
        "x86_64-i586",
        "armh",
        "aarch64",
        "ppc64le",
        "riscv64",
        "loongarch64",
        "mipsel",
        "e2k",
        "e2kv4",
        "e2kv5",
        "e2kv6",
    ]
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
    known_beehive_branches = [
        "sisyphus",
        "p11",
        "p10",
        "p9",
    ]
    known_beehive_archs = [
        "i586",
        "x86_64",
    ]

    known_image_components = ["iso", "rpms", "altinst", "live", "rescue"]

    known_image_platform = [
        "tegra",
        "rpi4",
        "baikalm",
        "mcom02",
        "hifive",
        "qemu",
        "oci",
        "k8s",
    ]

    known_image_editions = [
        "alt-server",
        "alt-server-v",
        "alt-container",
        "alt-education",
        "alt-workstation",
        "alt-kworkstation",
        "alt-virt-pve",
        "alt-sp-addon",
        "alt-sp-server",
        "alt-sp-workstation",
        "slinux",
        "cloud",
        "starterkit",
        "regular",
    ]
    known_image_archs = [
        "i586",
        "x86_64",
        "aarch64",
        "ppc64le",
        "armh",
        "riscv64",
        "mipsel",
    ]
    known_image_types = ["iso", "tar", "img", "qcow", "oci"]
    known_image_releases = ["alpha", "beta", "rc", "release"]
    known_image_variants = ["install", "live", "rescue"]

    gitalt_base = "https://git.altlinux.org"
    beehive_base = "https://git.altlinux.org/beehive"
    gitalt_tasks_base = "https://git.altlinux.org/tasks"
    packages_base = "https://packages.altlinux.org/en"
    bugzilla_base = "https://bugzilla.altlinux.org"
    public_ftp_base = "http://ftp.altlinux.org/pub/distributions/ALTLinux"
    errata_base = "https://errata.altlinux.org"
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
        "c10f2": ["c10f1", "p10", "sisyphus"],
        "c10f1": ["p10", "sisyphus"],
        "c9f2": ["c9f1", "p9", "sisyphus"],
        "c9f1": ["p9", "sisyphus"],
        # "c8.1": ["c8", "p8", "sisyphus"],
        # "c8": ["p8", "sisyphus"],
        # "c7.1": ["c7", "p7", "sisyphus"],
        # "c7": ["p7", "sisyphus"],
        "p11": ["sisyphus"],
        "p10": ["sisyphus"],
        "p9": ["sisyphus"],
        # "p8": ["sisyphus"],
        # "p7": ["sisyphus"],
        "sisyphus": ["sisyphus"],
    }
    branch_inheritance_root = "sisyphus"

    known_errata_type = {"packages": ["branch", "task"], "repository": ["bulletin"]}

    errata_branch_update_prefix = "ALT-BU"
    errata_package_update_prefix = "ALT-PU"
    errata_change_prefix = "ALT-EC"
    errata_advisory_prefix = "ALT-SA"

    errata_ref_type_bug = "bug"
    errata_ref_type_vuln = "vuln"
    errata_ref_type_branch = "branch"
    errata_ref_type_errata = "errata"

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

    comment_ref_type_errata = "errata"
    comment_ref_type_task = "task"
    comment_ref_type_web = "web"
    comment_ref_type_package = "package"

    comment_ref_types = (
        errata_ref_type_bug,
        errata_ref_type_vuln,
        comment_ref_type_errata,
        comment_ref_type_task,
        comment_ref_type_web,
        comment_ref_type_package,
    )

    default_reason_source_type_exclusion = "exclusion"
    default_reason_source_type_cpe = "cpe"
    default_reason_source_type_comment = "comment"
    default_reason_source_type_pnc = "pnc"

    default_reason_source_types = (
        errata_ref_type_vuln,
        comment_ref_type_errata,
        comment_ref_type_task,
        default_reason_source_type_pnc,
        default_reason_source_type_cpe,
        default_reason_source_type_exclusion,
        default_reason_source_type_comment,
    )

    vuln_status_statuses = ("new", "analyzing", "working", "resolved")
    vuln_status_resolutions = ("not_for_us", "not_affected", "wont_fix", "our")
    vuln_status_json_fields = ("note", "project_name", "cpes")

    errata_user_last_activities_types = (
        "vuln_status",
        "comment",
        "errata",
        "exclusion",
        "cpe",
        "pnc",
    )


lut = LookupTables()
