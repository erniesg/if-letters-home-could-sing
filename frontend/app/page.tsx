'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Home() {
  const [showReveal, setShowReveal] = useState(false);
  const [showScroll, setShowScroll] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (showReveal) {
      console.log('🎭 Loading Reveal animation...');
      const revealIframe = document.createElement('iframe');
      revealIframe.style.position = 'fixed';
      revealIframe.style.top = '0';
      revealIframe.style.left = '0';
      revealIframe.style.width = '100%';
      revealIframe.style.height = '100%';
      revealIframe.style.border = 'none';
      revealIframe.src = 'http://localhost:8000/index.html';  // Explicitly point to index.html
      document.body.appendChild(revealIframe);

      // Listen for reveal completion
      const handleRevealMessage = (event) => {
        if (event.data === 'revealComplete') {
          console.log('🔄 Reveal complete, switching to Scroll Typography');
          document.body.removeChild(revealIframe);
          setShowReveal(false);
          setShowScroll(true);
        }
      };

      window.addEventListener('message', handleRevealMessage);
      return () => {
        window.removeEventListener('message', handleRevealMessage);
        if (document.body.contains(revealIframe)) {
          document.body.removeChild(revealIframe);
        }
      };
    }
  }, [showReveal]);

  useEffect(() => {
    if (showScroll) {
      console.log('📜 Loading Scroll Typography...');
      const scrollIframe = document.createElement('iframe');
      scrollIframe.style.position = 'fixed';
      scrollIframe.style.top = '0';
      scrollIframe.style.left = '0';
      scrollIframe.style.width = '100%';
      scrollIframe.style.height = '100%';
      scrollIframe.style.border = 'none';
      scrollIframe.src = 'http://localhost:1234/index2.html';  // Explicitly point to index2.html
      document.body.appendChild(scrollIframe);

      // Listen for scroll completion
      const handleScrollMessage = (event) => {
        if (event.data === 'scrollComplete') {
          console.log('🔄 Scroll Typography complete, redirecting to Sound page');
          document.body.removeChild(scrollIframe);
          setShowScroll(false);
          router.push('/sound');
        }
      };

      window.addEventListener('message', handleScrollMessage);
      return () => {
        window.removeEventListener('message', handleScrollMessage);
        if (document.body.contains(scrollIframe)) {
          document.body.removeChild(scrollIframe);
        }
      };
    }
  }, [showScroll, router]);

  if (showReveal || showScroll) {
    return null;
  }


  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Welcome to Heart Rate Monitor</h1>
      <Link
        href="/dashboard"
        className="mt-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
      >
        View Heart Rate Data
      </Link>
      <Link
        href="/sound"
        className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
      >
        Try Opera Sounds
      </Link>
    </div>
  );
}
