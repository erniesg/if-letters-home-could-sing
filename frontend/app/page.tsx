import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-black to-gray-900 text-white p-4">
      <h1 className="text-4xl font-bold mb-8">Welcome to Heart Rate Monitor</h1>
      <Link
        href="/dashboard"
        className="mt-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-full transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
      >
        View Heart Rate Data
      </Link>
    </div>
  );
}
