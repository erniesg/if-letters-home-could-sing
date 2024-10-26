import './globals.css'

export const metadata = {
  title: 'If Letters Home Could Sing',
  description: 'An interactive sound installation with visualization',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
