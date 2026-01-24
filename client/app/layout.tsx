import type { Metadata } from "next"
import Link from "next/link"
import { PT_Sans, PT_Serif } from "next/font/google"

import "./globals.css"

const serif = PT_Serif({
  subsets: ["cyrillic"],
  weight: ["400", "700"],
  variable: "--font-serif",
})

const sans = PT_Sans({
  subsets: ["cyrillic"],
  weight: ["400", "700"],
  variable: "--font-sans",
})

export const metadata: Metadata = {
  title: "Uni-RAG",
  description: "Загрузка и просмотр документов в Markdown",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru" className={`${serif.variable} ${sans.variable}`}>
      <body>
        <div className="shell">
          <header className="nav">
            <div className="logo">
              Uni-RAG
              <span>Документы в Markdown</span>
            </div>
            <nav className="nav-links">
              <Link className="pill" href="/">
                Главная
              </Link>
              <Link className="pill" href="/upload">
                Загрузка
              </Link>
              <Link className="pill" href="/documents">
                База документов
              </Link>
            </nav>
          </header>
          <main>{children}</main>
        </div>
      </body>
    </html>
  )
}
