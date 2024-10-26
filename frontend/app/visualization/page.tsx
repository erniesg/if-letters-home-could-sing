// app/visualization/page.tsx
'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Motion, Plus, X, ZoomIn } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import * as tf from '@tensorflow/tfjs';
import { Letter, SeriesConnections, Position } from '../types/letters';

// Utility functions
const encodeGeoAssociation = (geo: string): number[] => {
  // Implement your encoding logic here
  // This is a simplified example
  const locations = ['London', 'Paris', 'New York'];
  return locations.map(loc => (geo === loc ? 1 : 0));
};

const encodeMaterial = (material: string): number[] => {
  // Implement your encoding logic here
  const materials = ['Paper', 'Parchment', 'Canvas'];
  return materials.map(mat => (material === mat ? 1 : 0));
};

const LetterVisualization: React.FC = () => {
  const [letters, setLetters] = useState<Letter[]>([
    {
      id: 1,
      scmsId: "SCMS001",
      artist: "John Doe",
      dating: "1890",
      series: "A",
      seriesIndex: 1,
      material: "Paper",
      geoAssociation: "London",
      highlighted: false,
      size: 1,
      position: { x: 0, y: 0 }
    },
    // Add more sample data...
  ]);

  const [bpm, setBpm] = useState<number>(70);
  const [selectedLetter, setSelectedLetter] = useState<Letter | null>(null);
  const [viewPosition, setViewPosition] = useState<Position>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(1);

  const performTSNE = async (data: Letter[]): Promise<Position[]> => {
    // Convert letter metadata to numerical features
    const features = data.map(letter => {
      return [
        parseInt(letter.dating) || 0,
        letter.seriesIndex || 0,
        ...encodeGeoAssociation(letter.geoAssociation),
        ...encodeMaterial(letter.material)
      ];
    });

    const tensorData = tf.tensor2d(features);
    const normalized = tf.div(
      tf.sub(tensorData, tf.min(tensorData)),
      tf.sub(tf.max(tensorData), tf.min(tensorData))
    );

    // Perform t-SNE
    const tsne = tf.serialization.fromConfig({
      perplexity: 30,
      learningRate: 10,
      nIterations: 1000
    });

    const tsneResult = await tsne.fit(normalized);
    const positions = await tsneResult.arraySync() as number[][];

    // Scale positions to viewport
    return positions.map(([x, y]) => ({
      x: (x + 1) * window.innerWidth / 2,
      y: (y + 1) * window.innerHeight / 2
    }));
  };

  useEffect(() => {
    const initializePositions = async () => {
      const positions = await performTSNE(letters);
      setLetters(prev => prev.map((letter, i) => ({
        ...letter,
        position: positions[i]
      })));
    };

    initializePositions();
  }, []);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      const MOVE_AMOUNT = 50;
      switch(e.key) {
        case 'ArrowLeft':
          setViewPosition(prev => ({ ...prev, x: prev.x - MOVE_AMOUNT }));
          break;
        case 'ArrowRight':
          setViewPosition(prev => ({ ...prev, x: prev.x + MOVE_AMOUNT }));
          break;
        case 'ArrowUp':
          setViewPosition(prev => ({ ...prev, y: prev.y - MOVE_AMOUNT }));
          break;
        case 'ArrowDown':
          setViewPosition(prev => ({ ...prev, y: prev.y + MOVE_AMOUNT }));
          break;
        case '+':
          setZoom(prev => Math.min(prev + 0.1, 2));
          break;
        case '-':
          setZoom(prev => Math.max(prev - 0.1, 0.5));
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  const seriesConnections = useMemo<SeriesConnections>(() => {
    const series: SeriesConnections = {};
    letters.forEach(letter => {
      if (letter.series) {
        if (!series[letter.series]) {
          series[letter.series] = [];
        }
        series[letter.series].push(letter);
      }
    });
    return series;
  }, [letters]);

  // Mock BPM update - replace with actual Whoop integration
  useEffect(() => {
    const interval = setInterval(() => {
      setBpm(prev => prev + (Math.random() * 10 - 5));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  // Update sizes based on BPM
  useEffect(() => {
    setLetters(prev => prev.map(letter => ({
      ...letter,
      size: letter.highlighted ? 1 + (bpm - 60) / 60 : 1
    })));
  }, [bpm]);

  return (
    <div className="relative w-full h-screen bg-slate-900 overflow-hidden">
      {/* Controls */}
      <div className="absolute top-4 left-4 text-white space-y-2 z-10">
        <div className="flex items-center gap-2">
          <Motion className="w-4 h-4" /> BPM: {Math.round(bpm)}
        </div>
        <div className="flex items-center gap-2">
          <Plus className="w-4 h-4" /> Use arrow keys to navigate
        </div>
        <div className="flex items-center gap-2">
          <ZoomIn className="w-4 h-4" /> Use +/- to zoom
        </div>
      </div>

      {/* Visualization Container */}
      <div
        className="absolute inset-0 transition-transform duration-200"
        style={{
          transform: `translate(${viewPosition.x}px, ${viewPosition.y}px) scale(${zoom})`
        }}
      >
        {/* Series Connections */}
        <svg className="absolute inset-0 pointer-events-none">
          {Object.entries(seriesConnections).map(([series, seriesLetters], seriesIndex) => (
            seriesLetters.map((letter, i) => {
              if (i === seriesLetters.length - 1) return null;
              const next = seriesLetters[i + 1];
              return (
                <line
                  key={`series-${letter.id}-${next.id}`}
                  x1={letter.position.x}
                  y1={letter.position.y}
                  x2={next.position.x}
                  y2={next.position.y}
                  stroke={`hsla(${seriesIndex * 30}, 70%, 50%, 0.2)`}
                  strokeWidth="1"
                  strokeDasharray="5,5"
                />
              );
            })
          ))}
        </svg>

        {/* Letters */}
        {letters.map((letter) => (
          <div
            key={letter.id}
            className={`absolute transition-all duration-500 cursor-pointer
              ${letter.highlighted ? 'text-yellow-400' : 'text-white'}`}
            style={{
              left: letter.position.x,
              top: letter.position.y,
              transform: `scale(${letter.size})`,
            }}
            onClick={() => setSelectedLetter(letter)}
          >
            <div className="w-3 h-3 rounded-full bg-current" />
            {letter.highlighted && (
              <div className="absolute -inset-1 rounded-full bg-current opacity-20 animate-pulse" />
            )}
            <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs whitespace-nowrap">
              {letter.seriesIndex && `Series ${letter.series} - ${letter.seriesIndex}`}
            </div>
          </div>
        ))}
      </div>

      {/* Letter Detail Modal */}
      <Dialog open={!!selectedLetter} onOpenChange={() => setSelectedLetter(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              {selectedLetter?.artist}
              <X
                className="w-4 h-4 cursor-pointer"
                onClick={() => setSelectedLetter(null)}
              />
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <h4 className="font-medium">Date</h4>
              <p>{selectedLetter?.dating}</p>
            </div>
            {selectedLetter?.series && (
              <div>
                <h4 className="font-medium">Series Information</h4>
                <p>Series {selectedLetter.series} - Letter {selectedLetter.seriesIndex}</p>
              </div>
            )}
            <div>
              <h4 className="font-medium">Geographic Association</h4>
              <p>{selectedLetter?.geoAssociation}</p>
            </div>
            <div>
              <h4 className="font-medium">Material</h4>
              <p>{selectedLetter?.material}</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LetterVisualization;
