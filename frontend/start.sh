#!/bin/bash

echo "🧹 Clearing caches..."

# Fix npm cache permissions first
# echo "🔧 Fixing npm cache permissions..."
# sudo chown -R $(whoami) "/Users/$(whoami)/.npm"

# Clear npm cache
npm cache clean --force
echo "✨ NPM cache cleared"

# Clear Next.js cache
rm -rf .next
echo "✨ Next.js cache cleared"

# Clear Parcel cache and ensure Parcel is installed
cd public/scroll
rm -rf .parcel-cache dist
npm install parcel --save-dev
echo "✨ Parcel cache cleared and dependencies installed"
cd ../..

echo "🚀 Starting servers..."

# Start http-server for reveal in background
cd public/reveal
npx http-server -p 8000 --no-cache -c-1 &
REVEAL_PID=$!
echo "✅ Reveal server started on port 8000"

# Start scroll server in background
cd ../scroll
npx parcel src/index2.html --no-autoinstall &
SCROLL_PID=$!
echo "✅ Scroll server started"

# Start Next.js dev server
cd ../..
npm run dev &
NEXTJS_PID=$!
echo "✅ Next.js server started"

# Function to handle script termination
cleanup() {
    echo "⏳ Shutting down servers..."
    kill $REVEAL_PID
    kill $SCROLL_PID
    kill $NEXTJS_PID
    echo "👋 All servers stopped"
    exit
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

echo "🌟 All servers are running!"
echo "📌 Access the app at http://localhost:3000"

# Keep script running
wait
