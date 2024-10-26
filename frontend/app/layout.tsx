import './globals.css'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'If Letters Home Could Sing',
  description: 'An interactive sound installation with visualization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
