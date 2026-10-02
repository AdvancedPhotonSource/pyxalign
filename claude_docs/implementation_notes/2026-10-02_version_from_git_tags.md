# Derive package version from git tags — 2026-10-02

## Problem

`pyproject.toml` carried a hand-maintained `version = "1.2.0"` field that had
already drifted from reality: `pip show pyxalign` in an existing editable
install reported `1.0.0` while `pyproject.toml` said `1.2.0`, and master had
moved several commits past the `v1.2.0` tag with no version bump at all.
Nothing tied the installed package's version string to the actual git tag.

## Solution

Switched to `setuptools_scm`, which derives the version from git tags at
build/install time instead of a static string.

### `pyproject.toml`
- `[build-system] requires` now includes `setuptools_scm>=8`.
- `[project]` no longer has a static `version`; it declares
  `dynamic = ["version"]`.
- New `[tool.setuptools_scm]` section sets
  `version_file = "src/pyxalign/_version.py"`, which generates a small module
  containing `__version__`/`version_tuple`/`commit_id` on every build/install.

### `src/pyxalign/__init__.py`
- Imports `__version__` from the generated `._version` module (falls back to
  `"unknown"` if the file doesn't exist, e.g. a raw checkout that's never been
  installed). Added to `__all__`.

### `.gitignore`
- `src/pyxalign/_version.py` is generated on every install/build and must not
  be tracked — added alongside the existing `*egg-info*` ignore.

## Versioning behavior

- On a clean tag (e.g. `v1.2.0`) with no further commits and a clean working
  tree: version is exactly `1.2.0`.
- N commits past the last tag: `1.2.1.dev{N}+g{hash}` (setuptools_scm's
  default `guess-next-dev` scheme — it assumes the next tag will be a patch
  bump and marks everything since as a dev pre-release of that).
- Dirty working tree (uncommitted changes): adds a `.d{date}` local segment,
  and since a dirty tree is "past" the tag, the version also reflects the
  post-tag dev scheme above rather than reading as the clean tag.
- Tags must look like `vX.Y.Z` (standard PEP 440-compatible); the existing
  `v1.2.0` tag already follows this.

## Migration guidance

- Anyone with an existing editable install must re-run `pip install -e .` to
  pick this up — `pip show pyxalign` will otherwise keep showing stale,
  hand-edited metadata.
- This does **not** change the tagging workflow discussed with the user:
  tags are still created manually after merging to `master` (see git history/
  conversation context), e.g. `git tag -a v1.3.0 -m "..." && git push origin
  v1.3.0`. Nothing here auto-creates tags. Immediately after this change,
  master is untagged past `v1.2.0`, so `pyxalign.__version__` will read as a
  `1.2.1.dev{N}+...` dev version until the next tag is pushed.
- CI (`.github/workflows/python-app.yml`) already checks out with
  `fetch-depth: 0`, and both Dockerfiles copy the full repo (including `.git`,
  since there's no `.dockerignore` excluding it) before running
  `pip install -e .` — so no CI/Docker changes were needed for tag history to
  be visible during the build.

## Verification performed

- `pip install -e .` followed by `python -c "import pyxalign; print(pyxalign.__version__)"`
  — produced a `1.2.1.dev32+g0bd945f65.d20261002`-style version reflecting
  distance from `v1.2.0` plus the dirty tree from this change's own edits.
- Temporarily created a local `v9.9.9` tag on `HEAD` and reinstalled — version
  correctly tracked the new tag (showed as a dev/dirty variant of it, since
  the tree was still dirty from this change at the time); tag was deleted
  immediately after and never pushed.
