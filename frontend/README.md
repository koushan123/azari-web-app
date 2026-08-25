# Azari frontend

The frontend is a React 19 + TypeScript + Vite Persian/RTL accounting client for
the existing `/api/v1` backend. It contains no sample financial or prediction
records.

## Structure

- `auth/`, `theme/`, and `routes/`: session JWT, persistent preferences, and SPA routing
- `services/` and `types/`: centralized HTTP behavior and API contracts
- `components/`: states, fields, dialogs, formatting, and lightweight charts
- `pages/`: dashboard, accounting, reports, administration, and AI workflows
- `utils/`: English-digit financial formatting and dual-calendar conversion

## Commands

```powershell
npm.cmd run dev
npm.cmd run typecheck
npm.cmd run build
.\test.cmd
```

Set `VITE_API_URL` to the browser-reachable API base. The default is
`http://localhost:8100/api/v1`.

## UX and security

Light is the default theme; theme and calendar choices use local storage. The
JWT uses session storage, not source code or persistent local storage. The UI
hides actions outside a user's permission set and still handles backend 403
responses because backend RBAC is authoritative. All meaningful UI strings are
Persian; numeric output deliberately uses English digits.

IRANSans is referenced only as the first installed-font preference. No
commercial font is bundled. Calendar attribution is in `THIRD_PARTY_NOTICES.md`.
