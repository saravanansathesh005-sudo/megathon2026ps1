import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AEGIS",
  description: "AI assistant with automatic runtime security",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Display face for the assistant screens. The security terminal keeps its
            monospace look via .font-mono in globals.css. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
