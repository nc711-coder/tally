import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tally: ask your data",
  description: "Ask a business database questions in plain English and get the answer, a chart and the SQL behind it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
