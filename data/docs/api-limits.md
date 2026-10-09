# API usage
This is a fictional AcmeDesk handbook used only for the demo.

## Rate limits
The standard API limit is 120 requests per minute for each workspace.
Requests above the limit receive HTTP 429. Respect the Retry-After response header.
Use exponential backoff with jitter when retrying rate-limited requests.

## Authentication
Send a workspace API token in the Authorization bearer header.
Rotate API tokens from Settings, Integrations, API credentials.
Do not include API credentials in URLs or public source repositories.
