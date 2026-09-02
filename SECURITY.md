# Security policy - teaching repository

This repository contains **demo credentials only**. Never reuse them outside the ephemeral lab.

- Do not commit `.env`, access tokens, institutional credentials, certificates or real customer data.
- Use GitHub Actions Secrets for registry credentials.
- Keep database ports private in Codespaces; business traffic enters through the edge on port 8080.
- Treat HMAC credentials in `travel-benefits-api` as a teaching primitive, not a production identity solution.
- For production, replace local passwords with a secrets manager, enforce OIDC/mTLS, image signing and vulnerability scanning.
