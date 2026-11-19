import { NextResponse, type NextRequest } from "next/server";

export const SESSION_COOKIE = "pa_session";

/**
 * Sends visitors without a session cookie to /login. This is a convenience only:
 * FastAPI checks the session on every API call.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/login" || request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
