'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Activity, Plus, X, ZoomIn, ZoomOut } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import * as d3 from 'd3';

const LetterVisualization = () => {
  const [letters, setLetters] = useState([
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
    },
    {
      id: 2,
      scmsId: "SCMS002",
      artist: "Jane Smith",
      dating: "1895",
      series: "A",
      seriesIndex: 2,
      material: "Canvas",
      geoAssociation: "Paris",
      highlighted: false,
      size: 1,
    },
    {
      id: 3,
      scmsId: "SCMS003",
      artist: "Bob Johnson",
      dating: "1900",
      series: "B",
      seriesIndex: 1,
      material: "Wood",
      geoAssociation: "New York",
      highlighted: false,
      size: 1,
    }
  ]);

  const [bpm, setBpm] = useState(70);
  const [selectedLetter, setSelectedLetter] = useState(null);
  const [viewPosition, setViewPosition] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const simulation = d3.forceSimulation(letters)
      .force('charge', d3.forceManyBody().strength(-50))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(10))
      .on('tick', ticked);

    function ticked() {
      const node = svg.selectAll('.node')
        .data(letters, d => d.id)
        .join('g')
        .attr('class', 'node')
        .attr('transform', d => `translate(${d.x},${d.y})`);

      node.selectAll('circle')
        .data(d => [d])
        .join('circle')
        .attr('r', d => 5 * d.size)
        .attr('fill', d => d.highlighted ? '#FFA500' : '#3B82F6')  // Orange when highlighted, blue otherwise
        .attr('stroke', '#000')  // Black border
        .attr('stroke-width', 1);

      node.selectAll('text')
        .data(d => [d])
        .join('text')
        .text(d => d.artist)
        .attr('dy', 15)
        .attr('text-anchor', 'middle')
        .attr('fill', '#000')  // Black text
        .attr('font-size', '10px');
    }

    return () => {
      simulation.stop();
    };
  }, [letters]);

  // Handle keyboard navigation with zoom
  useEffect(() => {
    const handleKeyPress = (e) => {
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

  console.log("Rendering LetterVisualization component");
  console.log("Letters:", letters);

  return (
    <div className="relative w-full h-screen bg-white overflow-hidden">
      {/* Controls */}
      <div className="absolute top-4 left-4 text-black space-y-2 z-10">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4" /> BPM: {Math.round(bpm)}
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
        <svg ref={svgRef}></svg>
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

      {/* Debug Information */}
      <div className="absolute bottom-4 left-4 text-black">
        Letters count: {letters.length}
      </div>
    </div>
  );
};

export default LetterVisualization;
