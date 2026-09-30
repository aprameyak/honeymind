import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "HoneyMind",
  description: "AI-Adaptive Honeypot Analytics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <Nav />
          <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-6 animate-enter">{children}</main>
        </div>
      </body>
    </html>
  );
}
