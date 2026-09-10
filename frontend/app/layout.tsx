import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AEGIS Security Control Center",
  description: "Autonomous Execution Guard & Impact Safety",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
