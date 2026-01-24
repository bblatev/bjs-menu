import './globals.css'
import type { Metadata } from 'next'
import { DM_Sans, Playfair_Display, JetBrains_Mono } from 'next/font/google'
import AdminLayout from '@/components/AdminLayout'

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
})

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
})

export const metadata: Metadata = {
  title: "V99 POS | Admin Dashboard",
  description: "Enterprise Restaurant POS System",
  icons: {
    icon: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${dmSans.variable} ${playfair.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-white text-gray-900 antialiased font-sans">
        <AdminLayout>
          {children}
        </AdminLayout>
      </body>
    </html>
  )
}
