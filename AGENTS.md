# AGENTS

## Purpose
- Capture repo-specific context and workflows for people and agents.

## Repo Overview
- ALTRepo API is a REST API for the ALT distribution repository database.
- Primary entry points: `altrepo-api` (Gunicorn) or `python3 -m altrepo_api`.
- API docs are exposed via Swagger at `/api/` when the service is running.

## Layout
- `altrepo_api/`: application package.
- `tests/`: unit and integration tests.
- `docker-compose.yml`, `Dockerfile`: containerized runtime.
- `docker-compose.tests.yml`, `Dockerfile-tests`: containerized test runs.
- `api.conf.example`, `api.conf.docker.example`: configuration templates.

## Configuration
- Default config path: `/etc/altrepo-api/api.conf`.
- Override with CLI arg or `ALTREPO_API_CONFIG` env var (highest priority).
- Key sections: `[DATABASE]`, `[APPLICATION]`, `[OTHER]` (logging/admin).
- Example configs are supplied in-repo: `api.conf.example`, `api.conf.docker.example`, `tests/api.conf.example`.

## Common Commands
- Run locally: `python3 -m altrepo_api /path/to/config.file`
- Run with Gunicorn binary: `altrepo-api /path/to/config.file`
- Run unit tests: `python3 -m pytest tests/unit`
- Run all tests: `python3 -m pytest`

## Docker
- Build: `docker-compose build`
- Run: `docker-compose up -d`
- Tests: `docker-compose -f docker-compose.tests.yml up --build && docker rm app-test`

## Deployment Notes
- Systemd and Nginx example files are shipped in RPM docs.
- WSGI entrypoint is `/usr/share/altrepo-api/wsgi.py` in packaged installs.

## Ownership
- Maintainers (descending contribution per `AUTHORS.txt`):
  - Danil Shein
  - Dmitry Lyalyaev
  - Anton Farygin
  - Andrey Bychkov
  - Anton Zhukharev
  - Evgeniy Martynenko
  - Yaroslav Bahtin
  - Ivan Orlovskij
