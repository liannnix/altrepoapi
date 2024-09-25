# Changelog
ALTrepo API changelog

# [1.19.9] - 2024-09-25

Regular API code updates and fixes.

### Added
### Changed
- update project license year and README
- `task/task_info`: add support for `states` request argument that used to distinguish task contents for particular try and iteration
### Fixed
- `tests\test_parser`: update `test_file_name_wc_type` test cases

# [1.19.8] - 2024-09-18

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `altrepo_api/libs/errata_service`: ErrataID service URL handling
- `api/management/sql`: fix gathering latests `task_changed` value for `DONE` task

# [1.19.7] - 2024-09-12

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `package/packages_by_file_names`:
  - update file name validator
  - add a list of files that are not belong to any package

# [1.19.6] - 2024-09-10

Regular API code updates and fixes.

### Added
- `altrepo_api/site_pkgset_info`: new endpoint `tasks_history`
- `altrepo_api/package`: new endpoint `packages_by_file_names`
### Changed
- project `flake8` settings
### Fixed
- `altrepo_api/parser`: `file_name_wc_type` validator regexp

# [1.19.5] - 2024-08-29

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `tests`: fix av_scan tests
- `altrepo_api/parser`: `file_name_wc_type` validator regexp
- `altrepo_api/image`: fix SQL compatibility with new CH version

# [1.19.4] - 2024-08-09

Regular API code updates and fixes.

### Added
- `api/antivirus_scan` namespace and routes
### Changed
### Fixed

# [1.19.3] - 2024-08-08

Regular API code updates and fixes.

### Added
### Changed
- `api/management`: update `/packages/open_vulns` route
### Fixed
- `api/management`: fix SQL compatibility with new CH version
- `tests/with_database/test_management`: fix missing assertions, update tests

# [1.19.2] - 2024-08-05

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `api/[package|task]/what_depends_src`: fix SQL errors with CH v24.3.4

# [1.19.1] - 2024-07-11

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `api/vulnerabilities`: revert SQL request bug introduced in v1.19.0

# [1.19.0] - 2024-07-03

Regular API code updates and fixes.

### Added
### Changed
- `api/management`: make `Errata` object hashable
### Fixed
- `api`: fix SQL requests to be compatible with ClickHouse v24.3.4
- fix fragile tests

# [1.18.9] - 2024-06-07

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `errata/export/oval`: use branch inheritance to collect errata for OVAL XML files export

# [1.18.8] - 2024-06-03

Regular API code updates and fixes.

### Added
- `management`: add `vuln/list` route
### Changed
### Fixed
- `management`: fix `cpe/manage[PUT]` route

# [1.18.7] - 2024-05-30

Regular API code updates and fixes.

### Added
### Changed
- use `registry.altlinux.org` instead of `Docker Hub`
### Fixed

# [1.18.6] - 2024-05-27

Regular API code updates and fixes.

### Added
- `api/export/repology`: support for `p11` branch
### Changed
### Fixed

# [1.18.5] - 2024-05-24

Regular API code updates and fixes.

### Added
- initial support for `p11` branch
### Changed
### Fixed

## [1.18.4] - 2024-05-20

Regular API code updates and fixes.

### Added
### Changed
- `management/packages/open_vulns`: add vulnerability modified date field
### Fixed
- `api/bug`: SQL requests (closes #50388)

## [1.18.3] - 2024-05-16

Regular API code updates and fixes.

### Added
- `management`: clone several routes from `api` namespace for convenience
### Changed
### Fixed

## [1.18.2] - 2024-05-03

Regular API code updates and fixes.

### Added
### Changed
- **Breaking change** `api/site/binary_package_scripts`: add pretrans and postrans scripts support (closes #50149). Requires DB version 2.14.0
### Fixed

## [1.18.1] - 2024-05-03

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `management/task/list`: fix subtasks gathering for `EPERM` tasks

## [1.18.0] - 2024-05-02

Regular API code updates and fixes.

### Added
- `site/package_info`: add VCS tag info
- `dependencies/fast_lookup` route
### Changed
- `management/task`:
  - `info`: return tasks in 'DONE', 'EPERM' and 'TESTED' states
  - `list`: return tasks in 'DONE', 'EPERM' and 'TESTED' states; add filter by status
- `management/packages/open_vulns`:
  - add filter by image name
  - retrieve hidden images
- `errata/find_erratas`: extend search type options
- `dependencies/what_depends_src`: make the `dp_type` argument optional
- minor code refactoring
### Fixed
- `task_progress/find_tasks`: fix SQL query for deleted subtasks
- `task/needs_approval`: fix server error on ceratin cases

## [1.17.4] - 2024-04-05

Regular API code updates and fixes.

### Added
### Changed
- update project dependencies
### Fixed
- bug introduced in v1.17.3
- `management`: implement failsafe Errata ID update

## [1.17.3] - 2024-04-01

Regular API code updates and fixes.

### Added
- `api`: support for temporary DB name from configuration
- `api/management`: use temporary DB name prefixing in `DELETE FROM` mutations wrapper
- **Breaking change** `api/management`: pass temporar DB name to `PackageCVEMatcher` class instances. Requires `altrepodb_libs` version 2.13.12+
### Changed
### Fixed
- `api/site_package/changelog`: fix validator upper bound

## [1.17.1] - 2024-03-28

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `api/auth`: token parsing errors handling

## [1.17.0] - 2024-03-28

Regular API code updates and fixes.

### Added
- merged `errata_namagement` branch
### Changed
### Fixed
- API arguments validation flaws

## [1.15.29] - 2024-03-11

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `/task/progress/task_info`: fix task architectures handling

## [1.15.29] - 2024-03-11

Regular API code updates and fixes.

### Added
- `api/vuln/cve`: collect related BDU IDs
### Changed
- `api/vuln`: use all branches for package name to project name mapping
### Fixed
- `api/task_progress/find_tasks`: handling of package names with `_` symbols

## [1.15.28] - 2024-02-16

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `auth`: LDAP group membership check
- `tests/authorization`: tests and test assets

## [1.15.27] - 2024-02-15

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `vuln/cve/fixes`: branch' task inheritance algo

## [1.15.26] - 2024-02-14

Regular API code updates and fixes.

### Added
- `auth`: support for nested LDAP groups
### Changed
### Fixed

## [1.15.25] - 2024-02-12

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `/task/progress/task_info`: subtasks gathering SQL request
- `/api/auth`: user IP gathering when proxied

## [1.15.24] - 2023-12-28

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `/vuln/cve/fixes`: fix task history handling
- `/vuln/bdu/fixes`: fix task history handling

## [1.15.23] - 2023-12-25

Regular API code updates and fixes.

### Added
- `errat/find_image_erratas` route
### Changed
### Fixed

## [1.15.22] - 2023-12-13

Regular API code updates and fixes.

### Added
- `vuln/cve/fixes` route
- `vuln/bdu/fixes` route
### Changed
### Fixed

## [1.15.21] - 2023-12-06

Regular API code updates and fixes.

### Added
- `export/translation`: add `from_date` optional argument support
- support for `loongarch64` architecture
### Changed
### Fixed

## [1.15.20] - 2023-12-01

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `vuln/common`: fix task history handling
- `vuln/cve/packages`: extend affected packages search algorithm

## [1.15.19] - 2023-11-23

Regular API code updates and fixes.

### Added
- `site_package/package_info_brief` route
### Changed
- `task_progress/taskinfo`: force to use task progress as a source for tasks in 'FAILED' state
### Fixed

## [1.15.18] - 2023-11-21

Regular API code updates and fixes.

### Added
- `dependencies/what_depends_src` route
### Changed
### Fixed
- `site/fast_packages_search_lookup` result handling

## [1.15.17] - 2023-11-20

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `api/vuln`: increase CVE matching algorithm efficiency

## [1.15.16] - 2023-11-14

Regular API code updates and fixes.

### Added
- `task/needs_approval`: support for `before` argument
### Changed
- `api/dependencies`: remove dead code
### Fixed
- `task/needs_approval`: task check logic

## [1.15.15] - 2023-11-13

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `what_depends_src`: fix architectures defaults for ports branches

## [1.15.14] - 2023-11-13

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `task/task_info`: fix task `DELETED` tasks handling

## [1.15.13] - 2023-11-09

Regular API code updates and fixes.

### Added
### Changed
- `api/site_packageset`: suupport virtual `srpm` architecture
### Fixed

## [1.15.12] - 2023-11-07

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `task/task_info`: fix task data gathering for tasks in `NEW` state

## [1.15.11] - 2023-10-24

Regular API code updates and fixes.

### Added
- `api/errata`: add initial `c10f2` branch support
### Changed
- `api/errata`: check for errata discard
### Fixed
- logging to console: split messageas to stderr/stdout by log level

## [1.15.10] - 2023-10-20

Regular API code updates and fixes.

### Added
- API logging: support for `APP_LOGGING_TAG` environment variable
### Changed
### Fixed

## [1.15.9] - 2023-09-28

Regular API code updates and fixes.

### Added
- optional `no_chache` argument support:
  * `task/misconflict`
  * `task/what_depends_src`
### Changed
### Fixed
- `task/task_info`: esponse result serialization

## [1.15.8] - 2023-09-28

Regular API code updates and fixes.

### Added
- `site/watch_by_maintainer`: add latest packages versions from Repology
- add `c10f2` branch support
### Changed
- `task/`: add `no_cache` argument upport in `/task_info`, `/misconflict` and `what_depends_src` routes
### Fixed
- `task/check_images`: fix SQL request

## [1.15.6] - 2023-09-04

Regular API code updates and fixes.

### Added
### Changed
- `errata/find_erratas`: `type` argument allowed values
### Fixed
- `api/vuln`: packages' CPE matches SQL request for multiple matching records
- `task/needs_approval`: finally fixed endpoint business logic

## [1.15.5] - 2023-09-04

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `task/needs_approval`: algorithm error

## [1.15.4] - 2023-08-31

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `api/file`: fix binary packages search for version related file paths

## [1.15.3] - 2023-08-31

Regular API code updates and fixes.

### Added
### Changed
- `api/file`: use case sensitive search to improve performance for 2 to 7 times 
### Fixed
- fragile (DB contents dependent) tests
- `api/errata`: URLs for vulnerabilities that has no data in DB

## [1.15.2] - 2023-08-28

Regular API code updates and fixes.

### Added
### Changed
- `api/vuln` endpoints uses task and branch inheritance history when search for erratas and open vulnerabilities
### Fixed
- tests failed due DB contents changed

## [1.15.1] - 2023-08-22

Regular API code updates and fixes.

### Added
- `export/branch_tree` route
- `task/check_images` route
### Changed
- add `c9f1` branch in `known_approvers` LUT used in `task/needs_approval` route
### Fixed
- exclude `icarus` branch in `find_erratas` route SQL request
- fix missing tasks in `site/last_packages_by_tasks` endpoint results due to limit argument handling in SQL request

## [1.15.0] - 2023-08-11

Regular API code updates and fixes.

### Added
- `/errata/errata_branches` route
- `/errata/find_erratas` route
- `/vuln/task` route
- `/auth` namespace and routes
- `file_storage` backend for authorization tokens storage
### Changed
- use file_storage backand as default for authorization tokens
- update configuration examples
- update project dependencies
- update Docker files
### Fixed
- code style flaws
- routes descritpion and docstrings

## [1.14.4] - 2023-08-04

Regular API code updates and fixes.

### Added
- `task/needs_approval` route
### Changed
### Fixed
- `dependencies/backport_helper`: implementation logic
- `acl/maintainer_groups`: fix SQL request and tests
- using MVs in SQL requests

## [1.14.3] - 2023-07-14

Regular API code updates and fixes.

### Added
### Changed
- `api/vuln`: do not strip vulnerabilities JSON representation objects from results
### Fixed

## [1.14.2] - 2023-07-13

Regular API code updates and fixes.

### Added
- `vuln/branch` route
- `vuln/maintainer` route
### Changed
- `api/vuln`: hide unstable endpoints
### Fixed

## [1.14.1] - 2023-07-12

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- `errata/branches_updates` fix serializer error

## [1.14.0] - 2023-07-11

Regular API code updates and fixes.

### Added
### Changed
- **Breaking change**: refactored `api/vuln` and `api/errata` code to use new `ErrataHistory` table structure form ALTRepo DB version 2.10.0+
### Fixed

## [1.13.2] - 2023-06-23

Regular API code updates and fixes.

### Added
- `errata/ids` route
- `errata/search` route
- `errata/branches_updates` route
- `errata/packages_updates` route
### Changed
### Fixed
- code formatting using black
- minor code errors and typos

## [1.13.1] - 2023-06-19

Regular API code updates and fixes.

### Added
### Changed
- `errata/export/oval`: BDU collecting by CVE ids is now disabled by default due to changes in Errata generation in ALTRepo DB version 2.9.0+
### Fixed

## [1.13.0] - 2023-06-16

Regular API code updates and fixes.

### Added
- `vuln/cve/packages` route
- `vuln/bdu/packages` route
- `vuln/package` route
- `site_package/package_misconflict` route
- `site_package/package_name_from_repology` route
### Changed
### Fixed
- delete debug printout

## [1.12.1] - 2023-06-01

Regular API code updates and fixes.

### Added
- `api/vuln` routes namespace
### Changed
- enabled `c10f1` branch for OVAL export
### Fixed

## [1.11.3] - 2023-05-26

Regular API code updates and fixes.

### Added
- `errata/export/oval`: support for upcoming `c10` branch
### Changed
- `errata/export/oval`: product CPE list in `<advisory><affected_cpe_list>` section for `p9` and `p10` branches
### Fixed
- `errata/export/oval`: branch detection regular expressions

## [1.11.2] - 2023-05-19

Regular API code updates and fixes.

### Added
- `packageset/packages_by_component route` route
### Changed
### Fixed

## [1.11.1] - 2023-05-17

Regular API code updates and fixes.

### Added
- `c10f1` branch support
- `task/progress/find_tasks`: `by_package` request parameter
### Changed
- deprecate `site/tasks_by_package` route
- deprecate `site/tasks_by_maintainer` route
### Fixed

## [1.11.0] - 2023-05-12

Regular API code updates and fixes.

### Added
### Changed
- remove legacy unused data
- speed-up particular SQL requests
### Fixed

## [1.10.6] - 2023-05-11

Regular API code updates and fixes.

### Added
### Changed
- package/repocop: optimize SQL request
### Fixed
- libs/oval: Textfilecontent54State xml tag name

## [1.10.5] - 2023-04-27

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- site/package_info: fix deleted packages handling
- site/find_packages: fix search results relevance sorting

## [1.10.4] - 2023-04-21

Regular API code updates and fixes.

### Added
- BDU data in OVAL definitions
### Changed
- added `by_binary` feild in `site/find_packages` route response
### Fixed
- `site/find_packages` multiword search error

## [1.10.2] - 2023-04-20

Regular API code updates and fixes.

### Added
- `errata` routes namespace
- `errata/export/oval` routes
### Changed
- `site/find_packages` and `site/fast_packages_search_lookup` now support search by multiple words
### Fixed
- source package build time in `site/package_info` route (closes: #41537)
- `site/find_packages` and `site/fast_packages_search_lookup` maximum words quantity set to first 3, others are ignored

## [1.9.6] - 2023-03-31

Regular API code updates and fixes.

### Added
### Changed
**Breaking change**
- change file related request namespace `files` -> `file`
- route name `files/file_search` -> `file/search`
- route name `files/fast_file_search_lookup` -> `file/fast_lookup`
- `file/search` argument names
- `file/fast_lookup` argument names
### Fixed
- `file` routes code errors
- `file/search` route logic
- `file/fast_lookup` route result relevance

## [1.9.5] - 2023-03-30

Regular API code updates and fixes.

### Added
- `file` namespace and routes
    **Note**: requires FileSearch table
- `task/packages` route
- `acl/maintainer_groups` route
- `dependencies/backport_helper` route
### Changed
- API routes namespaces order in SwaggerUI
### Fixed
- `acl/by_packages` request arguments validation (closes #43540)

## [1.9.4] - 2023-03-14

Regular API code updates and fixes.

### Added
- acl/by_packages route
- debug logging of total request elapsed time
### Changed
- /task/progress/task_info: add source package name and hash
### Fixed

## [1.9.3] - 2023-03-05

Regular API code updates and fixes.

### Added
- utils: make_tmp_table_name()
- task/find_images route
### Changed
- updated copyright year
- code refactored to use make_tmp_table_name()
- refactored site/task_info enpoint code
- custom JSON serializer: class -> function
### Fixed
- libs/package_dependencies: ambiguous provides handling error
- task/find_images: find only images enabled by edition and tag simultaneously

## [1.9.2] - 2023-02-16

Regular API code updates and fixes.

### Added
- support loggign to console (stderr)
### Changed
### Fixed

## [1.9.1] - 2023-02-14

Regular API code updates and fixes.

### Added
- support for custom response headers
### Changed
### Fixed
- multithreading logging issues (partially)
- site/package_info: search build task algorithm (closes #45195)
- site/Package_downloads_src: use same build task algorithm as site/package_info route

## [1.9.0] - 2022-12-12

Regular API code updates and fixes.

### Added
- task/progress routes namespace
### Changed
- **Breaking change**: requires GlobalSearch, TaskProgress and TaskSubtaskProgress tables (`ALTRepoDB v2.6.0`)
### Fixed
- site/deleted_package_info: missing deleted source packages
- site/package_changelog: changelog order (closes #44443)
- image/parser: arguments definitions
- api: variables and constants naming errors

## [1.8.11] - 2022-11-22

Regular API code updates and fixes.

### Added
- 'icarus' as known branch
- task/progress endpoints
### Changed
### Fixed
- site/find_packages architecture argument handling
- export/repology binary packages sorting

## [1.8.10] - 2022-11-03

Regular API code updates and fixes.

### Added
### Changed
- lut.known_archs contains only actual binary packages architectures
### Fixed
- code style errors
- routes descriptions
- api/packageset: fixed repository_packages route code package architecture handling

## [1.8.9] - 2022-11-03

Regular API code updates and fixes.

### Added
- site_packageset/find_source_package route
### Changed
- tests: implement skipped tests in test_utils
### Fixed
- tests: test_conflict_filter

## [1.8.8] - 2022-10-27

Regular API code updates and fixes.

### Added
### Changed
- removed dependency on librpm python bindings package `rpm` (`python3-module-rpm`)
- using custom librpm.so.7 functions wrappers from `api/libs/liprm_fucntions` module
### Fixed

## [1.8.7] - 2022-10-26

Regular API code updates and fixes.

### Added
### Changed
- tests: add test duration statistics for test Docker image
### Fixed
- site/pkgsets_summary_status: fix sorting

## [1.8.6] - 2022-10-18

Regular API code updates and fixes.

### Added
### Changed
### Fixed
- site/package_info: fix misleading hashes for 'noarch' binary packages 

## [1.8.5] - 2022-10-12

Regular API code updates and fixes.

### Added
### Changed
- exclude files from conflict packages if they are equal as `apt` and `rpm` does
### Fixed
- misconflict packages dependency version compare with librpm

## [1.8.4] - 2022-10-07

Regular API code updates and fixes.

### Added
- packageset/repository_statistics route
- packageset/packages_by_uuid route
- found ambiguous dependencies in {package|task}/build_dependency_set routes
### Changed
- {package|task}/build_dependency_set routes argument name: 'archs' -> 'arch'
- {package|task}/build_dependency_set routes argument type: list[str] -> str 
### Fixed
- code style errors
- closes bug #43478
- ambiguous provide dependencies resolved in a way as `apt` does as close as possible
- build dependency resolving using dependency name, version and flags through librpm functions

## [1.8.3] - 2022-09-27

Regular API code updates and fixes.

### Added
- python3-module-packaging dependency in docker files
### Changed
### Fixed
- Flask 2.2.x library compatibility
- updated requirements.txt

## [1.8.2] - 2022-08-23

Regular API code updates and fixes.

### Added
- search for deleted packages (closes #43539)
### Changed
- **Breaking change**: `site/find_packages` route data model
### Fixed

## [1.8.1] - 2022-08-09

Refactored APIWorker base class to reduce SQL requests related boilerplate code.

### Added
### Changed
### Fixed

## [1.8.0] - 2022-07-13

Merge new features in master branch for production use.

### Added
- 'nick' fields in site_package/* routes
- acl/* routes namespace
- bug/bugzilla_by_image_edition route
### Changed
- tests excleuded from python package
- 
### Fixed
- code style using black and flake8
- image version valdiation
- gear links for arepo packages
- export/translation trailing whitespaces
- package groups and subgroups matching
- package build task search

## [1.7.0] - yyyy-mm-dd

Merge new features in master branch for production use.

### Added
### Changed
### Fixed
- fixed image information related routes

## [1.6.3] - 2022-04-13

Regular API code updates and fixes.

### Added
- image/active_images route
- build task information for binary packages in site/package_info route
### Changed
- update parser
- requires BranchPackageHistory in DB
### Fixed
- added '%' symbol escaping in export/translation

## [1.6.2] - 2022-04-08

Regular API code updates and fixes.

### Added
- 'export/translation' route
- 'license/*' routes
- 'site_image/*' routes
- 'license/*' routes
### Changed
### Fixed
- added missing download links for 'x86_64-i568' (arepo) binary packages
- packages from task in tests Docker image

## [1.6.1] - 2022-03-18

Regular API code updates and fixes.

### Added
- unit and functional tests
- 'image/*' routes for frontend

### Changed
- updated README.md

### Fixed
- request argument validators
- 'what_depends_src' SQL requets errors

## [1.6.0] - 2022-02-14

Regular API code updates and fixes.

### Added
- e2kv6 architecture support
- 'export/branch_binary_packages route' route
- 'image/*' API namespace and routes
- ISO image related validators and look-up tables
- UUID serialization support

### Changed
- reduced routes boilerplate code duplication
- updated license years
### Fixed
- 'task/misconflict' route error on huge tasks (#41813)
- 'task/task_repo' code for built postponed tasks


## [1.5.4] - 2022-01-10

Regular API code updates and fixes.

### Added
- 'export/sitemap_packages' route

### Changed
- added tailing slashes in 'export/repology' route to avoid redirects
- modified regular expressions in custom validators

### Fixed
- mistypes and spelling
- type hints

## [1.5.3] - 2021-12-17

Regular API code updates and fixes.

### Added
- p10_e2k branch support
- 'site/pkghash_by_nvr' route

### Changed

### Fixed
- missing tzdata package in Docker file
- removed x86_64-i586 repository from Docker file
- packages watch by ACL to use latest data 

## [1.5.2] - 2021-12-14

Improved API security and stability with custom query arguments validators.
Added Docker container build files.

### Added
- Docker container build files
- custom JSON encoder that handles datetime serialisation
- updated README.md file
### Changed
- parsers machinery moved to separate `parsers.py` file
- use custom argument validators in all API arguments parsers
### Fixed
- closed bug #41537
- added 'task_date' field to result if task found.
## [1.5.1] - 2021-12-08
Update `/export/repology` API route
### Added
- added package epoch and release for `/export/repology`
### Changed
- updated README.md file
### Fixed
- fixed project Git repository URLs

## [1.5.0] - 2021-12-07
Ready for production and packaged as RPM for ALT Linux.
