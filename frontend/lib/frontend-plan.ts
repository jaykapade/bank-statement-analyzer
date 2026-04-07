export const backendCapabilities = [
  {
    eyebrow: "Backend shape",
    title: "The current product is job-centric",
    body: "Jobs move through pending, extracting, categorizing, completed, and failure states. The frontend should make that workflow obvious instead of pretending we already have a fully aggregated finance dashboard.",
  },
  {
    eyebrow: "Frontend implication",
    title: "Each uploaded file becomes a workspace",
    body: "The strongest first experience is upload -> watch status -> inspect extracted transactions -> retry failed categorization if needed.",
  },
];

export const appRoutes = [
  {
    href: "/upload",
    title: "Statement upload",
    summary:
      "File intake page for PDFs, upload errors, and redirecting users into the job flow.",
    endpoint: "POST /upload",
    state: "Build first",
  },
  {
    href: "/jobs",
    title: "Job history",
    summary:
      "List uploaded statements with filenames and current status so users can re-open previous work.",
    endpoint: "GET /jobs",
    state: "Build first",
  },
  {
    href: "/jobs/[jobId]",
    previewHref: "/jobs/demo-job",
    title: "Job detail",
    summary:
      "Polling workspace for processing states, counts, retry actions, and navigation into results.",
    endpoint: "GET /jobs/{job_id}",
    state: "Build first",
  },
  {
    href: "/jobs/[jobId]/transactions",
    previewHref: "/jobs/demo-job/transactions",
    title: "Transactions review",
    summary:
      "Table view for extracted rows and categories for one statement upload.",
    endpoint: "GET /transactions/{job_id}",
    state: "Build first",
  },
  {
    href: "/admin/reset",
    title: "Local reset",
    summary:
      "Development-only destructive tool to clear jobs and transactions in a local environment.",
    endpoint: "POST /reset",
    state: "Local only",
  },
];

export const workflowSteps = [
  {
    title: "Upload file",
    body: "Accept a PDF statement and send it to the backend as multipart form data.",
  },
  {
    title: "Track processing",
    body: "Poll job status while extraction and categorization run in the worker.",
  },
  {
    title: "Handle failures",
    body: "Surface extract failures, categorization failures, and queue outages clearly.",
  },
  {
    title: "Review rows",
    body: "Show the job's transactions in a sortable, filterable table once results are ready.",
  },
];

export const sampleJobs = [
  {
    Filename: "hdfc-april-statement.pdf",
    Status: "completed",
    "Job detail route": "/jobs/2c8f4f8e",
  },
  {
    Filename: "icici-march-statement.pdf",
    Status: "categorizing",
    "Job detail route": "/jobs/1af8ba22",
  },
  {
    Filename: "salary-account-feb.pdf",
    Status: "categorize_failed",
    "Job detail route": "/jobs/b7d133ca",
  },
];

export const jobsTableColumns = ["Filename", "Status", "Job detail route"];

export const sampleJobDetail = {
  status: "categorizing",
  total: 32,
  done: 27,
  failed: 3,
};

export const statusChecklist = [
  {
    status: "pending",
    kind: "active",
    description:
      "The upload exists and the page can already show the job, even before worker processing begins.",
  },
  {
    status: "extracting",
    kind: "active",
    description:
      "The worker is converting the PDF into text/markdown, so keep the user in a waiting state.",
  },
  {
    status: "categorizing",
    kind: "active",
    description:
      "Transactions have been saved and category assignment is underway. Counts become especially useful here.",
  },
  {
    status: "completed",
    kind: "stable",
    description:
      "All rows are categorized and the page should prioritize results review and summary metrics.",
  },
  {
    status: "categorize_failed / failed",
    kind: "needs-attention",
    description:
      "Offer retry when appropriate and explain whether the problem happened during categorization or more generally.",
  },
];

export const sampleTransactions = [
  {
    Date: "2026-04-01",
    Description: "Swiggy order",
    Amount: "$18.20",
    Category: "Food",
  },
  {
    Date: "2026-04-02",
    Description: "Uber trip",
    Amount: "$9.64",
    Category: "Transport",
  },
  {
    Date: "2026-04-03",
    Description: "Salary credit",
    Amount: "$1,540.00",
    Category: "Income",
  },
  {
    Date: "2026-04-03",
    Description: "Unknown merchant",
    Amount: "$291.00",
    Category: "Pending retry",
  },
];

export const transactionTableColumns = [
  "Date",
  "Description",
  "Amount",
  "Category",
];
