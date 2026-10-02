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

## Trusted Publishing workflow

The **Release package** workflow is manual-only. It builds one wheel and one source
distribution, validates them, uploads those exact artifacts to TestPyPI, and then
pauses at the protected `pypi` GitHub environment. Approve the PyPI job only after
installing and smoke-testing the TestPyPI release.

Before its first run, create separate TestPyPI and PyPI trusted publishers for:

- owner: `anser14`;
- repository: `free-hand-kit-auth`;
- workflow: `release.yml`;
- environments: `testpypi` and `pypi`, respectively;
- project: `freehand-kit-auth`.

Trusted Publishing exchanges GitHub's short-lived OIDC identity for an upload token;
do not create or store a PyPI API token in this repository. The workflow has no push,
tag, or pull-request trigger, so a maintainer must explicitly start every publication.
