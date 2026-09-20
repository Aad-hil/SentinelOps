# Security Policy

## Scope

SentinelOps is a portfolio/research project and is not intended to manage production infrastructure directly.

The project intentionally does not execute recovery actions against production systems.

## Reporting a vulnerability

Please do not disclose security-sensitive details in a public issue.

For a private report, use GitHub's private vulnerability reporting feature if it is enabled for this repository. Otherwise, contact the repository owner privately through their GitHub profile.

When reporting a vulnerability, include:

- affected component or file;
- reproduction steps;
- impact;
- relevant logs or stack traces;
- a suggested mitigation, if known.

## Secrets

Never commit:

- API keys;
- AWS credentials;
- database passwords;
- `.env` files;
- access tokens;
- private certificates.

Use `.env.example` as the configuration template.
