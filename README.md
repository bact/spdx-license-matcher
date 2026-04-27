# LicenseID

A modern, portable SPDX License ID matcher.

`licenseid` takes license text as input and identifies the closest matched SPDX License ID using a hybrid search strategy (SQLite FTS5 trigram + RapidFuzz ranking + optional Java validation).

## Features

- **Embedded Search**: Uses SQLite FTS5 with trigram tokenization for fast recall. No Redis required.
- **Hybrid Strategy**:
  - **Tier 1**: Broad recall using SQLite.
  - **Tier 2**: Precision ranking using RapidFuzz (Token Set Ratio).
  - **Tier 3**: Optional final validation via `tools-java` if available.
- **Modern Python**: Built for Python 3.10+ using Hatchling.
- **Unix Philosophy**: CLI output is parseable and predictable by default.

## Installation

```bash
pip install licenseid
```

Or using `uv`:

```bash
uv tool install licenseid
```

## Usage

### 1. Update the License Database
Before matching, you need to build the local license index:

```bash
licenseid update
```

### 2. Match a License
Match text from a file:

```bash
licenseid match LICENSE.txt
```

Or from a string:

```bash
licenseid match --text "This is a sample license text..."
```

### 3. Output Formats
Default (Unix-friendly):
```
LICENSEID=Apache-2.0 SCORE=0.9850
```

JSON:
```bash
licenseid match LICENSE.txt --json
```

## Configuration

- `SPDX_TOOLS_JAR`: Path to the `tools-java` jar for Tier 3 validation.

## License

Apache-2.0
