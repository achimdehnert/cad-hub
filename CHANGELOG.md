# Changelog

All notable changes to **cad-hub** will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Pin `nl2cad-core[ifc]` raised to `>=0.4.0,<1.0` (0.4.0 published on PyPI);
  `iil-nl2cadfw` raised to `>=0.2.1,<1` (latest published version).

### Removed
- Dead duplicate IFC parser `apps/ifc/parser/` (`IfcCompleteParser`, direct
  ifcopenshell usage, 5 files / ~2100 lines) — unreferenced outside its own
  folder. Active path stays `nl2cad.core.parsers.IFCParser` via
  `apps/ifc/services/ifc_parser.py`.
- Dead duplicate `apps/ifc/services/cad_loader.py` — broken relative imports
  (`.dxf_analyzer`/`.dxf_renderer` don't exist under `apps/ifc/services/`),
  0 active references anywhere in the repo.
- `nl2cad-nlp` and `iil-nl2cadfw` from `requirements.txt` — verified 0 imports
  of either in the codebase; `iil-nl2cadfw` was a redundant umbrella pin on
  top of the already-pinned individual `nl2cad-*` packages.

### Added
- authentik Single Sign-On on the nl2cad.de login page (ADR-142):
  `mozilla_django_oidc` app, per-app OIDC endpoints, `OIDC_ENABLED`
  gate, and a gated "IIL Single Sign-On" button.
- Initial CHANGELOG

