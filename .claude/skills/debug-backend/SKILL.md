---
name: debug-backend
description: Diagnose and fix backend bugs, errors, and exceptions. Use when the user reports a bug, shares an error log/stack trace, or asks to debug an issue.
allowed-tools: Read, Grep, Glob, Bash
metadata:
  tier: default
  cost: light
  side_effects: none
---

Debug the following backend issue:

$ARGUMENTS

## Debugging process

### Step 1: Understand the problem
- Parse the error message / stack trace
- Identify the error type and origin file:line

### Step 2: Trace the root cause
- Read the source code at the error location
- Trace the call chain upward
- Check related configuration files
- Look for recent changes that might have caused the issue

### Step 3: Identify the fix
- Determine the root cause (not just symptoms)
- Consider side effects of the fix
- Check if the same pattern exists elsewhere

### Step 4: Apply the fix
- Implement the minimal fix
- Explain WHY it fixes the problem
- Suggest a test case to prevent regression

## Common patterns to check
- NullPointerException → missing null checks or uninitialized dependencies
- SQL errors → query syntax, missing columns, type mismatches
- 401/403 → authentication/authorization configuration
- 500 → unhandled exceptions in service layer
- Connection errors → database/service configuration, connection pool exhaustion
- Serialization errors → DTO/entity field mismatches
