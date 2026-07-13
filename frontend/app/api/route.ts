import { NextResponse } from 'next/server';

// Live WHOOP OAuth belongs on the consented gateway and is disabled by default.
// The tablet/browser must never read a provider token or client secret.
export async function GET() {
  return NextResponse.json(
    { error: 'WHOOP aggregate context is disabled' },
    { status: 503 }
  );
}
