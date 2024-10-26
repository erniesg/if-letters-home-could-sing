'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'

const IntroPage = dynamic(() => import('./components/IntroPage'), { ssr: false })

export default function Home() {
  const [showIntro, setShowIntro] = useState(true)

  if (showIntro) {
    return <IntroPage onIntroComplete={() => setShowIntro(false)} />
  }

  return (
    <div>
      {/* Your main application content */}
      <h1>Main Application</h1>
      {/* This is where you'll implement your constellation of letters */}
    </div>
  )
}
