const WHOOP_API_HOSTNAME = process.env.WHOOP_API_HOSTNAME || 'https://api.prod.whoop.com';
const ACCESS_TOKEN = process.env.WHOOP_ACCESS_TOKEN || '';

console.log('WHOOP_API_HOSTNAME:', WHOOP_API_HOSTNAME);
console.log('ACCESS_TOKEN (first 10 chars):', ACCESS_TOKEN.substring(0, 10) + '...');

if (!ACCESS_TOKEN) {
  console.error('ACCESS_TOKEN is missing');
  throw new Error('Missing required environment variable');
}

export async function fetchLastFiveCycles(): Promise<any[]> {
  console.log('Fetching last five cycles...');
  try {
    const response = await fetch(
      `${WHOOP_API_HOSTNAME}/developer/v1/cycle?limit=5`,
      {
        headers: {
          Authorization: `Bearer ${ACCESS_TOKEN}`,
        },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch cycles. Status:', response.status);
      throw new Error('Failed to fetch cycles');
    }

    const data = await response.json();
    console.log('Fetched cycles data:', JSON.stringify(data, null, 2));
    return data.records;
  } catch (error) {
    console.error('Error fetching cycle data:', error);
    return [];
  }
}

export async function fetchHeartRateData(): Promise<number> {
  console.log('Fetching heart rate data...');
  try {
    const response = await fetch(
      `${WHOOP_API_HOSTNAME}/developer/v1/cycle/recovery`,
      {
        headers: {
          Authorization: `Bearer ${ACCESS_TOKEN}`,
        },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch heart rate data. Status:', response.status);
      throw new Error('Failed to fetch heart rate data');
    }

    const data = await response.json();
    console.log('Fetched heart rate data:', JSON.stringify(data, null, 2));
    return data.resting_heart_rate;
  } catch (error) {
    console.error('Error fetching heart rate data:', error);
    return 0;
  }
}
