import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/nav/Nav";

export const metadata: Metadata = {
  title: "Aditya Tapshalkar — ML/AI Engineer",
  description: "ML/AI engineer building systems that think.",
  openGraph: {
    title: "Aditya Tapshalkar",
    description: "ML/AI engineer building systems that think.",
    url: "https://tapshalkar.com",
    siteName: "Aditya Tapshalkar",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="pt-12">{children}</main>
      </body>
    </html>
  );
}
