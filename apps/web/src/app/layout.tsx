import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Inter, JetBrains_Mono } from "next/font/google";

import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const instrument = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:8080";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Oportuna — Inteligencia global de oportunidades tecnológicas",
    template: "%s · Oportuna",
  },
  description:
    "Hackathons, eventos, becas y programas para construir tu carrera tecnológica. Cada oportunidad con fuente original, fecha de comprobación y verificación explicable.",
  applicationName: "Oportuna",
  keywords: [
    "hackathons",
    "becas tecnológicas",
    "oportunidades tech",
    "eventos de tecnología",
    "startups",
    "investigación",
  ],
  openGraph: {
    title: "Oportuna — Tu próxima oportunidad, ya verificada",
    description:
      "Inteligencia global de oportunidades tecnológicas con procedencia verificable y recomendaciones según tu tiempo disponible.",
    type: "website",
    locale: "es_PE",
    siteName: "Oportuna",
  },
  twitter: {
    card: "summary_large_image",
    title: "Oportuna — Tu próxima oportunidad, ya verificada",
    description: "Oportunidades tecnológicas globales, verificadas y explicadas.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#f3f0e7",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${inter.variable} ${instrument.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen bg-paper text-ink antialiased">
        <a
          href="#contenido"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:text-paper-raised"
        >
          Saltar al contenido
        </a>
        <SiteHeader />
        <main id="contenido" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
