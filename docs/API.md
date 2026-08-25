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
| POST/GET/PATCH | `/parties[/{id}]` | `parties:write/read` | Maintain counterparties |
| POST/GET/PATCH | `/products[/{id}]` | `products:write/read` | Maintain products/services |
| POST/GET | `/account-categories` | `accounts:write/read` | Maintain account categories |
| POST/GET/PATCH | `/accounts[/{id}]` | `accounts:write/read` | Maintain the chart of accounts |
| POST/GET | `/periods` | `periods:manage/read` | Create/list financial periods |
| POST | `/periods/{id}/close` | `periods:manage` | Close a period |
| POST/GET | `/journals[/{id}]` | `journals:write/read` | Create/list/read draft journals |
| POST | `/journals/{id}/post` | `journals:post` | Atomically validate and post |
| POST | `/journals/{id}/reverse` | `journals:post` | Create a posted opposite entry |
| POST/GET | `/invoices[/{id}]` | `invoices:write/read` | Create/list/read invoices |
| POST | `/invoices/{id}/issue` | `invoices:issue` | Issue through the posting engine |
| POST/GET | `/payments[/{id}]` | `payments:write/read` | Create/list/read allocated payments |
| POST | `/payments/{id}/post` | `payments:post` | Post payment and allocations atomically |
| GET | `/reports/trial-balance` | `reports:read` | Posted debit/credit totals by account |
| GET | `/reports/income-statement` | `reports:read` | Revenue, expenses, and net income |
| GET | `/reports/revenue` | `reports:read` | Revenue account activity |
| GET | `/reports/expenses` | `reports:read` | Expense account activity |
| GET | `/reports/balance-sheet` | `reports:read` | Assets, liabilities, equity, current earnings |
| GET | `/reports/receivables` | `reports:read` | Historical outstanding/overdue invoices |
| GET | `/reports/payables` | `reports:read` | Posted liability-account exposure |
| GET | `/reports/cash-flow` | `reports:read` | Posted customer cash receipts by date |
| GET | `/reports/parties/{id}/history` | `reports:read` | Party invoice/payment history |
| GET | `/dashboard` | `reports:read` | Operational financial aggregates |
| GET | `/ml/models` | `ml:read` | List safe registered-model metadata |
| GET | `/ml/models/{pipeline}/active` | `ml:read` | Get the explicitly active version |
| POST | `/ml/models/register` | `ml:manage` | Validate/register a controlled artifact identifier |
| POST | `/ml/models/{id}/activate` | `ml:manage` | Atomically activate one pipeline version |
| POST | `/ml/transactions/classify` | `ml:predict` | Classify text and persist the result |
| POST | `/ml/payment-risk/predict` | `ml:predict` | Score an invoice from cutoff-safe history |
| POST | `/ml/cash-flow/forecast` | `ml:predict` | Forecast 1–365 days from an as-of cutoff |
| POST | `/ml/segmentation/predict` | `ml:predict` | Assign a customer using cutoff-safe behavior |
| GET | `/ml/predictions[/{id}]` | `ml:read` | Read append-oriented prediction history |
| POST | `/ml/predictions/{id}/feedback` | `ml:feedback` | Append feedback or a comment |

Registration accepts `email`, `password`, `first_name`, and `last_name`. Extra
fields are rejected, so callers cannot inject an ADMIN role. Passwords must be
12–128 characters and are never returned. Login returns
`{"access_token":"...","token_type":"bearer"}`. Missing/invalid/expired tokens
return 401; authenticated users without the required permission receive 403.

Clients provide invoice quantities, prices/taxes, and account selections but
never trusted totals or derived statuses. Business conflicts return 409,
domain validation failures return 422, and missing resources return 404.

Report endpoints accept ISO date filters. Statement/cash-flow endpoints accept
`start_date` and `end_date`; balance sheet, receivables, payables, and dashboard
accept `as_of`; receivables optionally accepts `customer_id`. Invalid ranges
return 422. Draft/cancelled ledger activity is excluded as appropriate.

Model responses expose versions and safe metadata but never artifact filesystem
paths. Missing active models return 404, duplicate registration conflicts return
409, invalid artifacts or prediction cutoffs return 422, and authentication or
permission failures remain 401/403. Prediction inputs exclude credentials and
are not stored wholesale.
