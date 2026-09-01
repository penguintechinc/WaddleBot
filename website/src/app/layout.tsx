import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Waddles - Multi-Platform Chat Bot System",
  description: "A modular, microservices architecture chat bot system for Discord, Twitch, and Slack communities. Built with Python, py4web, and Kubernetes for scalability.",
  keywords: ["chatbot", "discord", "twitch", "slack", "microservices", "python", "kubernetes", "community management"],
  authors: [{ name: "Waddles Team" }],
  openGraph: {
    title: "Waddles - Multi-Platform Chat Bot System",
    description: "A modular, microservices architecture chat bot system for Discord, Twitch, and Slack communities.",
    type: "website",
    siteName: "Waddles",
  },
  twitter: {
    card: "summary_large_image",
    title: "Waddles - Multi-Platform Chat Bot System",
    description: "A modular, microservices architecture chat bot system for Discord, Twitch, and Slack communities.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
