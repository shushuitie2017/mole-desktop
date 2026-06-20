---
name: test
description: Generate unit tests and integration tests for backend code. Use when the user asks to write tests, create test cases, or says "test".
disable-model-invocation: true
metadata:
  tier: default
  cost: light
  side_effects: none
---

Generate tests for the following code or module:

$ARGUMENTS

## Instructions

1. Detect the project's existing test framework (JUnit / Spock / pytest / Jest / etc.)
2. Follow the project's existing test patterns and directory structure
3. Generate comprehensive test cases

## Test coverage requirements

### Happy path
- Normal input and expected output
- All main business logic branches

### Edge cases
- Null / empty / boundary values
- Maximum and minimum values
- Special characters in strings

### Error cases
- Invalid input
- Exception scenarios
- Unauthorized access

### Mock strategy
- Mock external dependencies (database, HTTP calls, third-party services)
- Use the project's mocking framework (Mockito / MockK / unittest.mock / etc.)

## Output format

- Place test files in the correct test directory following project conventions
- Use descriptive test method names that explain WHAT is being tested and WHAT is expected
- Include setup/teardown if needed
- Add comments for complex test scenarios
