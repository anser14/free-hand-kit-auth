# Contributing to Freehand Kit Auth

Thank you for contributing. This package is intended to be a dependable reusable
Django component, so behavior, documentation, schema, and tests move together.

## Before opening a pull request

1. Discuss behavior changes in an issue or architecture decision record.
2. Keep the package independent of other future Freehand Kit modules.
3. Add success, failure, and security-focused tests for behavior changes.
4. Update the OpenAPI contract and user documentation with endpoint changes.
5. Run tests, linting, type checks, package builds, and package metadata checks.

## Compatibility

Do not widen supported dependency ranges merely because installation succeeds. A
range becomes supported only after it passes the documented CI and example-project
matrix.
