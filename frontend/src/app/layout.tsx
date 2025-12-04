import type { Metadata } from "next";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeltaCFO Agent",
  description: "AI-powered financial transaction processing and management",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Google Fonts - loaded via link for better compatibility */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&family=Sora:wght@100..800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-background antialiased font-sans">
        <Providers>
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              classNames: {
                toast: "bg-card border shadow-lg",
                title: "text-foreground font-medium",
                description: "text-muted-foreground",
                success: "border-green-200 bg-green-50",
                error: "border-red-200 bg-red-50",
                warning: "border-yellow-200 bg-yellow-50",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
