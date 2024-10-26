import Link from 'next/link'

export default function Home() {
  return (
    <div>
      <h1>Main Application</h1>
      {/* This is where you'll implement your constellation of letters */}
      <Link href="/intro">Back to Intro</Link>
    </div>
  )
}
