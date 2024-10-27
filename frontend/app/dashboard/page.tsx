'use client';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import HeartRateVisualization from '../../components/HeartRateVisualization';

export default function Dashboard() {
  const [cycles, setCycles] = useState([]);
  const [heartRate, setHeartRate] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchWhoopData() {
      console.log('Fetching WHOOP data...');
      try {
        const response = await fetch('/api');
        console.log('API response status:', response.status);
        if (!response.ok) {
          throw new Error('Failed to fetch WHOOP data');
        }
        const data = await response.json();
        console.log('Received data:', data);
        setCycles(data.cycles);
        setHeartRate(data.heartRate);
      } catch (err) {
        console.error('Error fetching WHOOP data:', err);
        setError('Failed to fetch WHOOP data');
      } finally {
        setLoading(false);
      }
    }

    fetchWhoopData();
  }, []);

  console.log('Rendering Dashboard. Cycles:', cycles, 'Heart Rate:', heartRate);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error}</div>;

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Your Heart Rate</h1>
      <HeartRateVisualization cycles={cycles} currentHeartRate={heartRate} />
      <Link
        href="/realtime-hr"
        className="mt-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
      >
        View Real-time Heart Rate
      </Link>
    </div>
  );
}
