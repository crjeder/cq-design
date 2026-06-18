## ADDED Requirements

### Requirement: Timeout is caught and treated as a call failure
The orchestrator `_call_claude()` function SHALL catch `subprocess.TimeoutExpired` and convert it to a `RuntimeError` so the calling retry loop handles it as a recoverable failure rather than crashing the process.

#### Scenario: claude -p exceeds timeout
- **WHEN** the `claude -p` subprocess does not return within the configured timeout
- **THEN** `_call_claude()` raises `RuntimeError` with a message that includes the word "timeout"

#### Scenario: timeout does not crash orchestrator
- **WHEN** `_call_claude()` raises due to timeout
- **THEN** the part-loop `except RuntimeError` handler catches it, records a failed attempt, and breaks the attempt loop (matching existing behaviour for other call failures)

### Requirement: Subprocess stdin is closed
`_call_claude()` SHALL pass `stdin=subprocess.DEVNULL` (or equivalent) so the child `claude` process never inherits an open stdin that could block on interactive input.

#### Scenario: non-interactive environment
- **WHEN** `claude -p` is invoked in a background task with no TTY
- **THEN** the subprocess does not hang waiting for stdin input

### Requirement: Prompt is passed via stdin, not positional argument
`_call_claude()` SHALL deliver the prompt text through the subprocess stdin stream rather than as a positional CLI argument, to avoid Windows command-line length limits.

#### Scenario: large prompt (>15 KB)
- **WHEN** the rendered prompt string exceeds 15 000 characters
- **THEN** `claude -p` receives the full prompt without truncation or argument-parse error

### Requirement: Non-interactive flag is set
`_call_claude()` SHALL include `--dangerously-skip-permissions` in the `claude -p` invocation so the child process never pauses for permission confirmations.

#### Scenario: child needs no interactive approval
- **WHEN** `claude -p` is invoked with `--dangerously-skip-permissions`
- **THEN** the subprocess completes without waiting for user input to approve any action

### Requirement: Timeout is configurable via environment variable
The call timeout SHALL be read from the `CLAUDE_TIMEOUT` environment variable (integer seconds). If the variable is absent or non-numeric, the default SHALL be 600 seconds.

#### Scenario: CLAUDE_TIMEOUT is set
- **WHEN** `CLAUDE_TIMEOUT=120` is in the environment
- **THEN** `_call_claude()` uses a 120-second timeout for `subprocess.run`

#### Scenario: CLAUDE_TIMEOUT is absent
- **WHEN** `CLAUDE_TIMEOUT` is not set
- **THEN** `_call_claude()` uses a 600-second default timeout
