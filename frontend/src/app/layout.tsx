import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { MainLayout } from "@/components/layout/main-layout";
import { APIProvider } from "@/lib/api-context";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Graph-RAG Research System",
  description: "Multi-LLM evaluation system for Berlin transport networks using Graph-RAG",
  keywords: ["Graph-RAG", "LLM", "Neo4j", "Berlin Transport", "Research"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <APIProvider>
          <MainLayout>{children}</MainLayout>
        </APIProvider>
      </body>
    </html>
  );
}
