# reference-download

## Purpose

The single bounded, sanctioned path for downloading a reference STL from the web.

## Requirements

### Requirement: fetch_stl.py is the only sanctioned reference download

`src/fetch_stl.py --url <url>` SHALL download a reference mesh to `build/refs/<first 16 hex chars of sha256>.stl` under the working directory and emit JSON with keys `success`, `errors`, `path`, `bytes`, `sha256`. The caller SHALL NOT be able to choose the output path or filename. `prompts/research.md` SHALL instruct this script for STL downloads and SHALL NOT contain an inline `urllib` or `curl` download.

#### Scenario: Successful download
- **WHEN** the URL serves a valid binary STL under the size cap
- **THEN** the file is written under `build/refs/`, `success` is true and `path`, `bytes` and `sha256` are set

#### Scenario: Research prompt uses the script
- **WHEN** `prompts/research.md` is rendered
- **THEN** its download step invokes `fetch_stl.py` and contains no `urlretrieve`

### Requirement: fetch_stl.py bounds what it accepts

The script SHALL reject any scheme other than `http` and `https`, follow at most 3 redirects, abort a download larger than 50 MB without leaving a file, and load the result with `mesh_io.load_mesh`. A file that fails to load SHALL be deleted and reported as an error. The script SHALL NOT apply a domain allowlist. Exit code SHALL be 0 on success and 1 on any rejection.

#### Scenario: Non-http scheme rejected
- **WHEN** the URL is `file:///etc/passwd`
- **THEN** `success` is false, no file is written and the error type names the scheme

#### Scenario: Oversized download aborted
- **WHEN** the response exceeds 50 MB
- **THEN** the download stops, no file remains in `build/refs/` and `success` is false

#### Scenario: Not an STL
- **WHEN** the URL serves an HTML page
- **THEN** the file is deleted and `success` is false with a parse error

#### Scenario: Any domain allowed
- **WHEN** the URL is a valid STL on a domain not in `skill_permissions.json`
- **THEN** the download succeeds
