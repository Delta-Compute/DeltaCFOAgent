"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { Globe } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { locales, localeNames, type Locale } from "@/i18n/config";

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("nav");

  function switchLocale(newLocale: Locale) {
    // Save to localStorage for persistence
    localStorage.setItem("preferred-locale", newLocale);

    // Remove existing locale prefix from pathname if present
    let cleanPath = pathname;
    for (const loc of locales) {
      if (pathname.startsWith(`/${loc}/`) || pathname === `/${loc}`) {
        cleanPath = pathname.replace(`/${loc}`, "") || "/";
        break;
      }
    }

    // Navigate to new locale path
    const newPath = newLocale === "en" ? cleanPath : `/${newLocale}${cleanPath}`;
    router.push(newPath);
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          <Globe className="h-4 w-4" />
          <span className="hidden md:inline">{t("language")}</span>
          <span className="text-xs text-muted-foreground uppercase">
            {locale}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((loc) => (
          <DropdownMenuItem
            key={loc}
            onClick={() => switchLocale(loc)}
            className={locale === loc ? "bg-accent" : ""}
          >
            <span className="mr-2">{getLanguageFlag(loc)}</span>
            {localeNames[loc]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Helper function to get flag emoji for each locale
function getLanguageFlag(locale: Locale): string {
  const flags: Record<Locale, string> = {
    en: "US",
    pt: "BR",
    es: "ES",
  };
  // Convert country code to flag emoji
  const code = flags[locale];
  return String.fromCodePoint(
    ...[...code].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65)
  );
}
