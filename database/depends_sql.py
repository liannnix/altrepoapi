from dataclasses import dataclass


@dataclass(frozen=True)
class SQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    get_pkg_binary_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_arch = '{arch}'
    AND pkg_sourcepackage = 0
"""

    get_depends_bin_pkg = """
SELECT
    dp_name,
    dp_version,
    dp_flag,
    dp_type
FROM Depends
WHERE pkg_hash = {pkghash}    
"""

    get_pkgs_name_and_arch = """
SELECT
    pkg_name,
    pkg_arch
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkgs_depends = """
SELECT pkg_hash
FROM last_depends
WHERE dp_name = '{dp_name}'
    AND pkgset_name = '{branch}'
    AND dp_type = '{dp_type}'
"""

    get_repo_packages = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_sourcepackage,
    pkg_buildtime,
    pkg_summary,
    pkg_packager_email,
    pkg_group_
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_hash IN (SELECT * FROM {tmp_table})
    AND pkg_buildtime >= 0
ORDER BY pkg_name
"""

    get_pkgset_depends = """
SELECT
    count(pkg_hash),
    pkgset_name
FROM last_depends
WHERE dp_name = '{dp_name}'
    AND dp_type = '{dp_type}'
group by pkgset_name
"""


dependencysql = SQL()