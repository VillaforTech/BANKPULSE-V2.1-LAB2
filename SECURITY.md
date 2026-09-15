# Security policy

BankPulse is a portfolio and development environment built with synthetic data and local demo credentials. Do not reuse those credentials or expose the default stack to the public Internet.

- Never commit `.env`, access tokens, institutional credentials, certificates or real customer data.
- Report a suspected vulnerability privately to the repository owner instead of opening an issue with exploit details.
- Keep database ports private; product traffic enters through the Nginx edge on port 8080.
- Store registry credentials in GitHub Actions Secrets.
- Treat the HMAC flow in `travel-benefits-api` as a demo credential mechanism, not production identity.
- Before a public deployment, add managed secrets, OIDC or mTLS where appropriate, image signing, dependency and container scanning, rate limits, audit retention and data-protection review.

Security improvements are welcome through focused pull requests with a threat, mitigation and verification method.
