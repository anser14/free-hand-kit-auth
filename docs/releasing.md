# Release process

Publish only immutable artifacts. A version uploaded to PyPI or TestPyPI must never be
reused.

## Release gate

1. Confirm all required GitHub Actions checks are green for the supported matrix.
2. Review Dependabot updates and the dependency-audit result.
3. Run the full local checks in [Testing](testing.md), including real PostgreSQL,
   Redis, and Mailpit coverage.
4. Run `python manage.py check --deploy` and `python manage.py check --tag fk_auth`
   with production-equivalent secrets and shared cache configuration.
5. Confirm the security-reporting channel in `SECURITY.md` is enabled and monitored.
6. Update the version, compatibility policy, and dated changelog entry.
7. Build once, upload the identical artifacts to TestPyPI, install them in a clean
   consumer project, and only then upload the same version to PyPI.

The repository never publishes automatically from CI. Publishing requires an explicit
maintainer action and PyPI trusted-publishing configuration or another protected
credential flow.
