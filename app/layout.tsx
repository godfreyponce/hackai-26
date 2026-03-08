import type { Metadata } from 'next'
import { Space_Grotesk, DM_Sans } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Navbar } from '@/components/navbar'
import { StarField } from '@/components/star-field'
import './globals.css'

const spaceGrotesk = Space_Grotesk({ 
  subsets: ["latin"],
  variable: '--font-heading',
  display: 'swap',
});

const dmSans = DM_Sans({ 
  subsets: ["latin"],
  variable: '--font-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Nebula Advisor | AI Academic Advisor for UTD Students',
  description: 'Your AI academic advisor, available 24/7. No appointment needed. Built for UTD students by Nebula Labs.',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${dmSans.variable}`}>
      <body className="font-sans antialiased bg-background text-foreground">
        <StarField />
        <Navbar />
        {children}
        <Analytics />
      </body>
    </html>
  )
}
