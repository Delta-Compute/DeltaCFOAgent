import createMiddleware from "next-intl/middleware";
import { locales, defaultLocale } from "./src/i18n/config";

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Don't redirect to locale prefix for default locale
  localePrefix: "as-needed",
});

export const config = {
  // Match all pathnames except for:
  // - API routes
  // - Static files
  // - Next.js internals
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
