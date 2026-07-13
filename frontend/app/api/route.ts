import { NextRequest, NextResponse } from 'next/server';
import { fetchLastFiveCycles, fetchHeartRateData } from '../../lib/whoopAuth';

export async function GET(request: NextRequest) {
  try {
    const cycles = await fetchLastFiveCycles();
    const heartRate = await fetchHeartRateData();

    return NextResponse.json({ cycles, heartRate });
  } catch {
    console.error('Unable to serve WHOOP data');
    return NextResponse.json({ error: 'Failed to fetch WHOOP data' }, { status: 500 });
  }
}
