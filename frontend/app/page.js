'use client';

import { useState } from 'react';
import IntroAnimation from '../components/IntroAnimation';

export default function Home() {
  const [introComplete, setIntroComplete] = useState(false);

  const handleIntroComplete = () => {
    setIntroComplete(true);
  };

  return (
    <div>
      {!introComplete && <IntroAnimation onComplete={handleIntroComplete} />}
      {introComplete && (
        <main>
          {/* Main content will go here */}
          <h1>Main Content</h1>
        </main>
      )}
    </div>
  );
}
