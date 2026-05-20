# Changelog

All notable changes to CNC Robot Control will be documented in this file.

This project follows a simple versioned release format. Use Git tags such as `v0.1.0` to publish release builds.

## [Unreleased]

### Added

- Cross-platform GitHub Actions release workflow for Windows, macOS, and Linux builds.
- VS Code workspace settings, launch configurations, tasks, and extension recommendations.
- Ruff and pytest configuration for local development and CI.

### Changed

- CI now runs against the Python version declared by the project.

## [0.1.0] - Initial Development

### Added

- Tkinter desktop application for CNC G-code workflow editing and control.
- Serial terminal support with `pyserial`.
- Flow editor, jog controls, templates, and G/M-code reference browser.
- Basic smoke test coverage.
