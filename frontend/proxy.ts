import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// We want to protect all routes EXCEPT these
const publicRoutes = ["/login", "/register"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Exclude static files, API routes, Next.js internals
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".") // e.g. favicon.ico
  ) {
    return NextResponse.next();
  }

  // The cookie name defined in the backend configuration
  const sessionCookie = request.cookies.get("finance_tracker_session");
  const isAuthenticated = !!sessionCookie?.value;

  const isPublicRoute = publicRoutes.includes(pathname);

  // If the user is NOT authenticated and trying to access a protected route
  if (!isAuthenticated && !isPublicRoute) {
    const loginUrl = new URL("/login", request.url);
    // Optional: add a ?redirect query param if you want to redirect them back after login
    // loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Ensure the middleware is only run for relevant paths
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
