---
name: review
description: Review backend code for bugs, security vulnerabilities, performance issues, and best practices. Use when the user asks for code review, wants to check code quality, or says "review".
allowed-tools: Read, Grep, Glob
metadata:
  tier: default
  cost: light
  side_effects: none
---

Review the following backend code thoroughly:

$ARGUMENTS

## Review checklist

Please check the code against these criteria:

### Security
- SQL injection, command injection, XSS, CSRF vulnerabilities
- Input validation and sanitization
- Authentication/authorization issues
- Sensitive data exposure (passwords, keys, tokens in code)

### Performance
- N+1 query problems
- Missing database indexes
- Unnecessary loops or redundant computations
- Memory leaks or resource not properly closed

### Code quality
- SOLID principles compliance
- Error handling completeness (try-catch, null checks)
- Naming conventions and readability
- Code duplication (DRY)

### Reliability
- Edge cases and boundary conditions
- Concurrency/thread safety issues
- Transaction management
- Proper logging

## Output format

For each issue found, provide:
1. **Severity**: Critical / Warning / Suggestion
2. **Location**: file:line_number
3. **Problem**: What's wrong
4. **Fix**: How to fix it with code example
