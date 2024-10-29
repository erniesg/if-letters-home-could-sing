import { NextRequest, NextResponse } from 'next/server';
import { fetchLastFiveCycles, fetchHeartRateData } from '../../lib/whoopAuth';

export async function GET(request: NextRequest) {
  console.log('API route /api/whoop called');
  try {
    console.log('Fetching cycles...');
    const cycles = await fetchLastFiveCycles();
    console.log('Fetched cycles:', cycles);

    console.log('Fetching heart rate...');
    const heartRate = await fetchHeartRateData();
    console.log('Fetched heart rate:', heartRate);

    console.log('Returning data from API route');
    return NextResponse.json({ cycles, heartRate });
  } catch (error) {
    console.error('An error occurred in API route:', error);
    return NextResponse.json({ error: 'Failed to fetch WHOOP data' }, { status: 500 });
  }
}
