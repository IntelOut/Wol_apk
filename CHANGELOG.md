# Changelog

All notable changes to this project will be documented in this file.

## [0.7.2] - 2026-06-08

### Added
- Clear button in Log viewer
- UI expand fixes for consistent card width in EN/RU locales

### Changed
- Version bumped to 0.7.2

## [0.7.1] - 2026-06-08

### Added
- Private IP validation (10.x, 172.16-31.x, 192.168.x)
- i18n (RU/EN) with language toggle in AppBar
- Log viewer inside the app
- Async timeout (10s) with correlation ID in WOL send
- Sentry breadcrumbs for UI actions
- Device `__slots__` for memory efficiency
- 13 new tests (private IP, log viewer, UI)

### Changed
- Version bumped to 0.7.1
- App title renamed to WakeOnLAN
- `Storage` class replacing global mutable state in storage.py
- SnackBar lifecycle fixed (new instance each call)
- Port validation (1-65535) on save and send
- Protocol `validate_ip` simplified, CVE-2023-45803 fix
- Drawer shows only current language privacy/agreement links
- Release APK/EXE named WakeOnLAN

### Removed
- Bulk wake (Wake selected) button
- Sort dropdown, group filter, interface selector

## [0.7.0] - 2026-06-08

### Added
- Private IP validation — only local network IPs allowed (10.x, 172.16-31.x, 192.168.x)
- `validate_private_ip()` function with 10 test cases
- i18n (RU/EN) with language toggle in AppBar
- Bulk wake with parallel async send (`asyncio.gather`)
- Device groups (group field + filter)
- Log viewer inside the app
- Network interface selector
- Sentry breadcrumbs for UI actions
- Async timeout (10s) with correlation ID in WOL send
- `Storage` class replacing global mutable state
- `Device.__slots__` for memory efficiency
- Structured test suite split into separate files (protocol, storage, UI, integration)
- File logging with rotation (`~/.wol_app_data/wol_app.log`)
- Sentry SDK integration for crash reporting (opt-in via consent)
- CHANGELOG.md for release tracking
- Smoke-test step in CD pipelines (APK/exe existence validation)
- Windows CI matrix in test workflow
- Canary/beta release workflow for `-rc` pre-release tags
- Screenshot testing infrastructure (`pytest-html` reports with `--screenshot`)
- `pyproject.toml` project section as single version source of truth

### Changed
- Version bumped to 0.7.0

## [0.6.1] - Previous

### Fixed
- Minor bug fixes and stability improvements
