# Security policy

## Supported versions

RepoLoop is pre-1.0 software. Security fixes are applied to the latest revision of the `main` branch.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Use [GitHub's private vulnerability reporting form](https://github.com/josephkehan-prog/repo-loop-harness/security/advisories/new) and include:

- the affected command or component;
- a minimal reproduction;
- potential impact;
- any suggested mitigation;
- whether the report involves secrets or private repository content.

Please avoid testing against systems or repositories you do not own or have permission to assess. Do not include live credentials or personal data in the report.

## Security boundaries

The current release is designed around these guarantees:

- discovery does not write to the inspected repository;
- repository content cannot expand machine policy or permissions;
- runtime commands fail closed without an explicit adapter;
- subprocess arguments are never passed through a shell;
- the browser GUI binds only to loopback and exposes no mutation route;
- repository-derived browser content is rendered as text;
- secrets are not intentionally collected or serialized.

If you find behavior that violates one of these boundaries, treat it as a security issue.
