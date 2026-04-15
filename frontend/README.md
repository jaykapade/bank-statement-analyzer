# Bank Statement Analyzer — Frontend

Next.js 16 frontend for the Bank Statement Analyzer. Provides authentication, PDF upload, job tracking, transaction display, and financial dashboards.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [Next.js 14](https://nextjs.org/) (App Router) |
| Language | TypeScript |
| Styling | Vanilla CSS (custom design system, dark mode) |
| Notifications | [Sonner](https://sonner.emilkowalski.dev/) |
| Icons | [Lucide React](https://lucide.dev/) |
| Package Manager | pnpm |

---

## Local Development

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). The app expects the backend running at `http://localhost:8000`.

---

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout — fetches current user server-side
│   ├── page.tsx                      # Dashboard (summary, charts)
│   ├── login/page.tsx                # Sign-in page
│   ├── register/page.tsx             # Registration page
│   ├── upload/page.tsx               # PDF upload
│   ├── jobs/
│   │   ├── page.tsx                  # Job list
│   │   └── [jobId]/
│   │       ├── page.tsx              # Job detail + debug dialogs
│   │       └── transactions/page.tsx # Transaction table for a job
│   └── admin/reset/page.tsx          # Reset all user data
├── components/
│   ├── app-shell.tsx                 # Sidebar layout — auth-aware nav + user card
│   ├── auth-form.tsx                 # Shared login/register form component
│   ├── logout-button.tsx             # Client-side logout button
│   ├── job-debug-dialogs.tsx         # PDF/markdown toggle viewer with copy support
│   └── upload-form.tsx               # Drag-and-drop PDF upload form
└── lib/
    ├── api.ts                        # API client (apiFetch, auth helpers, types)
    └── server-auth.ts                # Server-side getCurrentUserServer (reads cookie)
```

---

## Feature Status

### Authentication ✅
- [x] **User Registration & Login:** `/register` and `/login` pages with a shared `AuthForm` component.
- [x] **Cookie-Based Sessions:** `credentials: "include"` on all fetches; HTTP-only session cookie set by the backend.
- [x] **Server-Side User Resolution:** `getCurrentUserServer()` in `server-auth.ts` reads the session cookie on the server and passes the user to `RootLayout`.
- [x] **Auth-Aware Sidebar:** Shows user email + logout button when signed in; shows sign-in prompt and auth nav links when signed out.
- [x] **Auth Route Layout:** Login/register pages render without the main nav shell.

### Data Upload & Processing ✅
- [x] **Drag & Drop Interface:** Intuitive file upload zone for PDF bank statements.
- [x] **Upload Progress & Status:** Real-time polling for job status during background processing.
- [x] **Error Handling:** Toast notifications for upload failures and backend errors.

### Job Debug Viewer ✅
- [x] **PDF/Markdown Toggle:** `JobDebugDialogs` streams and renders the original PDF or extracted markdown from the backend asset endpoints.
- [x] **Copy to Clipboard:** One-click copy of the markdown content.
- [x] **Open in New Tab:** Direct link to raw PDF or markdown asset.

### Dashboard & Data Visualization ✅
- [x] **Summary Overview:** Key metrics (total income, total expenses, net savings).
- [x] **Transaction Table:** Sortable, filterable transactions per job.
- [x] **Interactive Charts:** Spending by category, income vs. expenses.
- [x] **Pagination:** Server-side pagination for large transaction sets.
- [x] **Dockerization:** Multi-stage `Dockerfile` and `docker-compose` integration with the backend.
- [x] **Manual Transaction Corrections:** Allow users to override AI-assigned categories inline.

### Planned
- [ ] **Protected Route Middleware:** Auto-redirect unauthenticated users to `/login` via Next.js middleware.
