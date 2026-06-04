# Tasks: Repository Restructure

**Input**: `specs/001-repository-restructure/spec.md` and `plan.md`

## Phase 1: Planning Artifacts

- [x] T001 Create implementation plan for package-first Python layout.
- [x] T002 Create task list for the restructure.

## Phase 2: Package Layout

- [x] T003 Create `igpsport_map_updater/` package.
- [x] T004 Move Python production modules into `igpsport_map_updater/`.
- [x] T005 Add root-level compatibility wrappers for existing Python CLI files.
- [x] T006 Convert internal imports to package-relative imports.

## Phase 3: Tests

- [x] T007 Update tests to import from `igpsport_map_updater`.
- [x] T008 Update monkeypatch targets to package module paths.
- [x] T009 Run `uv run pytest -q`.

## Phase 4: Command Compatibility

- [x] T010 Smoke test at least one root-level wrapper command.
- [x] T011 Confirm dry-run package workflow still emits old root command names.

## Phase 5: Documentation

- [x] T012 Update README project structure and contributor guidance for the package layout.
- [x] T013 Run final `git status --short` review for accidental generated artifacts.
