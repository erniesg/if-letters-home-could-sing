'use client';
import React, { useState, useEffect } from 'react';
import InteractiveText from './InteractiveText';
import MusicNoteParticle from './MusicNoteParticle';

const IntroPage: React.FC = () => {
  const [showMusicNote, setShowMusicNote] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowMusicNote(true);
    }, 3000); // Show music note after 3 seconds

    return () => clearTimeout(timer);
  }, []);

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh' }}>
      <InteractiveText />
      {showMusicNote && (
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
          <MusicNoteParticle />
        </div>
      )}
    </div>
  );
};

export default IntroPage;
