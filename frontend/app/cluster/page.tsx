'use client';

import React from 'react';
import LetterClusterVisualization from '@/components/letter-cluster';

const ClusterPage: React.FC = () => {
  return (
    <div className="w-full h-screen">
      <LetterClusterVisualization />
    </div>
  );
};

export default ClusterPage;
