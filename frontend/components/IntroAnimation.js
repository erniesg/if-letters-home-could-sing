'use client';

import { useState, useEffect } from 'react';

const IntroAnimation = ({ onComplete }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete();
    }, 5000); // Animation duration

    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className={`introContainer ${visible ? 'visible' : 'hidden'}`}>
      <h1 className="title">If Letters Home Could Sing</h1>
    </div>
  );
};

export default IntroAnimation;
