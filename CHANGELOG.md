# Changelog
ALTrepo API changelog
## [newrelease] - yyyy-mm-dd

### Added
### Changed
### Fixed

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
