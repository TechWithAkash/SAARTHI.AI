import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AuraChat from "@/components/AuraChat";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SAARTHI.AI - Smart AI for Adaptive Risk Tracking & Health Intelligence",
  description: "SAARTHI.AI - Smart AI for Adaptive Risk Tracking & Health Intelligence",
};



export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-[100dvh] flex flex-col bg-gray-50 text-gray-900`}>
        <main className="flex-1 h-full w-full flex flex-col">
          {children}
        </main>
        <AuraChat />
      </body>
    </html>
  );
}
