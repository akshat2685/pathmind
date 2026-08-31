import type { Metadata } from "next";
import { Bricolage_Grotesque, Source_Serif_4, Be_Vietnam_Pro, Caveat } from "next/font/google";
import "./globals.css";

const bricolageGrotesque = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  display: "swap",
});

const sourceSerif4 = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  display: "swap",
});

const beVietnamPro = Be_Vietnam_Pro({
  weight: ["400", "500", "600", "700"],
  variable: "--font-be-vietnam",
  subsets: ["latin"],
  display: "swap",
});

const caveat = Caveat({
  variable: "--font-caveat",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "PATHMIND — Mindful Learning Path Companion",
  description: "Evidence-Informed Career Counseling & Longitudinal Learning Navigation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className={`${bricolageGrotesque.variable} ${sourceSerif4.variable} ${beVietnamPro.variable} ${caveat.variable} antialiased text-on-surface`}
      >
        <div className="watercolor-overlay"></div>
        <div className="paper-texture"></div>
        {children}
      </body>
    </html>
  );
}
