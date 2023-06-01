# Changelog
ALTrepo API changelog
## [newrelease] - yyyy-mm-dd

### Added
### Changed
### Fixed

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
