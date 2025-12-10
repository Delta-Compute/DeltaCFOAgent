// Internationalization configuration for next-intl

export const locales = ["en", "pt", "es"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const localeNames: Record<Locale, string> = {
  en: "English",
  pt: "Portugues (Brasil)",
  es: "Espanol",
};

// Used for date/number formatting
export const localeConfigs: Record<Locale, { dateFormat: string; currency: string }> = {
  en: { dateFormat: "MM/dd/yyyy", currency: "USD" },
  pt: { dateFormat: "dd/MM/yyyy", currency: "BRL" },
  es: { dateFormat: "dd/MM/yyyy", currency: "USD" },
};
