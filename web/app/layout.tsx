import type { Metadata } from "next";
import { Archivo } from "next/font/google";
import { AskLauncher } from "@/components/AskLauncher";
import "./globals.css";

const archivo = Archivo({
  subsets: ["latin"],
  weight: ["400", "600", "800"],
  variable: "--font-archivo",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Empu",
  description: "Capture what masters know, before it's gone.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={archivo.variable} suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        {children}
        <AskLauncher />
      </body>
    </html>
  );
}
