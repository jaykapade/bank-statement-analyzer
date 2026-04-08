# Bank Statement Analyzer - Frontend

This is the frontend application for the Bank Statement Analyzer project, built with [Next.js](https://nextjs.org).

## Project Overview

The frontend serves as the user interface for the finance tracking system. It allows users to securely log in, upload their bank statements, view automated categorizations, and visualize their financial data through interactive dashboards.

## Implementation Plan & Roadmap

The following features are planned for future implementation.

### 1. Authentication
- [ ] **User Registration & Login:** Secure sign-up and login flow.
- [ ] **Session Management:** Handling JWT tokens securely (e.g., HTTP-only cookies).
- [ ] **Protected Routes:** Ensuring that only authenticated users can access their financial dashboards and upload data.

### 2. Data Upload & Processing
- [x] **Drag & Drop Interface:** An intuitive file upload zone for PDFs and CSV bank statements.
- [x] **Upload Progress & Status:** Real-time feedback during file upload and background processing (integrating with the backend task queue).
- [x] **Error Handling:** Clear notifications for unsupported file types or parsing failures.

### 3. Dashboard & Data Visualization
- [x] **Summary Overview:** Key metrics like total income, total expenses, and net savings for the selected period.
- [x] **Transaction Table:** A comprehensive view of all transactions with sorting, filtering, and pagination.
- [x] **Interactive Charts:** Visualizing spending by category, income vs. expenses, and historical trends.
- [ ] **Manual Adjustments:** Allowing users to manually correct AI-categorized transactions.

### 4. Dockerization
- [ ] **Dockerfile:** Creating a multi-stage Dockerfile optimized for a production Next.js build.
- [ ] **Docker Compose Integration:** Ensuring seamless integration with the existing backend and worker containers for easy local development and deployment.

### 5. UI/UX Enhancements
- [x] **Modern Aesthetics:** Implementing a clean, responsive design using a utility-first CSS framework or specialized UI components.
- [x] **Notifications System:** Toast notifications to keep the user informed about system alerts and errors.

---

## Local Development (Current Setup)

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.
