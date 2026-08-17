# API

The API is rooted at `/api/v1`; interactive OpenAPI documentation is served at
`/docs`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | Public | Process liveness; does not query dependencies |
| POST | `/auth/register` | Public | Create a normalized VIEWER account |
| POST | `/auth/login` | Public | Exchange JSON email/password for a bearer token |
| GET | `/auth/me` | Authenticated | Return the safe current-user representation |
| GET | `/users` | `users:read` | Return safe user records |

Registration accepts `email`, `password`, `first_name`, and `last_name`. Extra
fields are rejected, so callers cannot inject an ADMIN role. Passwords must be
12–128 characters and are never returned. Login returns
`{"access_token":"...","token_type":"bearer"}`. Missing/invalid/expired tokens
return 401; authenticated users without the required permission receive 403.
