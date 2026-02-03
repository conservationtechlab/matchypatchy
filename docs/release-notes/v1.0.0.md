# v1.1.0 — 2026-02-01

**Summary:** New GUI validation workflow and several performance improvements.

- Release tag / GitHub release: [v1.1.0](https://github.com/<owner>/<repo>/releases/tag/v1.1.0)
- Compare: [v1.0.0...v1.1.0](https://github.com/<owner>/<repo>/compare/v1.0.0...v1.1.0)
- Published: 2026-02-01
- Contributors: @alice, @bob, @kyra

## Highlights
- New interactive GUI validation workflow for re‑ID.
- Keyboard shortcuts for reviewers.
- Average matching latency reduced ~20%.

## Changelog (high level)
### Added
- GUI validation mode with reviewer queue.
- Keyboard shortcuts: n/p to cycle candidates, space to accept.

### Changed
- Matching algorithm performance improvements.
- Refactored matching cache (internal).

### Fixed
- Resolved nondeterministic ONNX scatter warning in some cases.
- Small UI layout bugs on Windows.

### Security
- No security fixes in this release.

## Migration notes
- If you upgrade from v1.0.0, remove any custom model cache directory: `~/.matchypatchy/cache` to avoid stale caches.

<details>
<summary>Full changelog / PRs (click to expand)</summary>

- PR #123 — Add GUI validation workflow (alice)
- PR #130 — Improve matching speed (bob)
- PR #131 — Fix ONNX nondeterminism (kyra)
- ... full list of PRs or bullet points ...

</details>