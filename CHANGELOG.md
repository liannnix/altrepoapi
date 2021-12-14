# Changelog
ALTrepo API changelog
## [newrelease] - yyyy-mm-dd

### Added
### Changed
### Fixed

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
