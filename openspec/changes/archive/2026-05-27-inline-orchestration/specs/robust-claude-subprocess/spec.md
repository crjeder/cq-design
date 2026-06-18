## REMOVED Requirements

### Requirement: Timeout is caught and treated as a call failure
**Reason**: _call_claude() is deleted with orchestrate.py. There is no subprocess to time out. Part generation is handled inline by Claude; if Claude is working, it is working.
**Migration**: None. Timeout handling for subprocess calls is no longer applicable.

---

### Requirement: Subprocess stdin is closed
**Reason**: _call_claude() is deleted. No claude subprocess is launched.
**Migration**: None.

---

### Requirement: Prompt is passed via stdin, not positional argument
**Reason**: _call_claude() is deleted. Claude constructs part prompts in-session by reading the template and substituting values, then uses that context directly. No stdin passing occurs.
**Migration**: None.

---

### Requirement: Non-interactive flag is set
**Reason**: _call_claude() is deleted. No child claude process is invoked.
**Migration**: None.

---

### Requirement: Timeout is configurable via environment variable
**Reason**: _call_claude() is deleted. The CLAUDE_TIMEOUT environment variable no longer has any effect.
**Migration**: None. Users who set CLAUDE_TIMEOUT can remove it from their environment.
