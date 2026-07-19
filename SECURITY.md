# Security policy

CausalPilot is a research prototype for local, reversible experimentation. It
is not a production control plane.

## Supported versions

Security fixes target the latest release and the `main` branch. Earlier commits
may remain vulnerable.

## Report a vulnerability privately

Use the repository's **Security → Report a vulnerability** flow to open a
private GitHub security advisory. Include:

- the affected commit or version;
- the smallest reproducible example;
- the expected and observed behavior;
- the security impact;
- a proposed fix, if available.

Do not open a public issue for an unpatched vulnerability. Do not include real
credentials, personal data, or third-party confidential data in a report.

## Deployment boundary

The local API has no authentication, authorization, rate limiting, tenant
isolation, or durable audit storage. Development CORS rules restrict browser
origins, but CORS is not an access-control mechanism. Bind the service to
`127.0.0.1` and use synthetic data.

The supplied containers run as unprivileged users and request read-only
filesystems. These controls reduce accidental damage; they do not make the
prototype safe for an untrusted network or irreversible business actions.

The static GitHub Pages build runs a seeded browser simulator. It does not
connect to the local API or execute external actions.

## Secrets and data

The default path requires no secret. Store optional credentials outside the
repository and inject them through the local environment. Never place secrets
in `NEXT_PUBLIC_*` variables because Next.js embeds those values in browser
assets.

Raw external datasets are excluded from version control. Review the source
license before downloading or processing any dataset.
