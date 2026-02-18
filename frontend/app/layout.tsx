import './globals.css'
import '@/styles/high-contrast.css'
import type { Metadata } from 'next'
import { DM_Sans, Playfair_Display, JetBrains_Mono } from 'next/font/google'
import AdminLayout from '@/components/AdminLayout'
import { Providers } from '@/components/Providers'
import OfflineIndicator from '@/components/OfflineIndicator'
import { SkipLink } from '@/components/ui/SkipLink'

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
    <html lang="en" className={`${dmSans.variable} ${playfair.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className="bg-white dark:bg-surface-900 text-gray-900 dark:text-surface-100 antialiased font-sans">
        <SkipLink />
        <OfflineIndicator />
        <Providers>
          <AdminLayout>
            <main id="main-content">
              {children}
            </main>
          </AdminLayout>
        </Providers>
      </body>
    </html>
  )
}
