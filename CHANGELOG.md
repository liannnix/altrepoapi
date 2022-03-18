# Changelog
ALTrepo API changelog
## [newrelease] - yyyy-mm-dd

### Added
### Changed
### Fixed

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
