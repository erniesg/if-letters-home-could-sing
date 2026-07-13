const WHOOP_API_HOSTNAME = process.env.WHOOP_API_HOSTNAME || 'https://api.prod.whoop.com';

function getWhoopAccessToken(): string | null {
  return process.env.WHOOP_ACCESS_TOKEN || null;
}

export async function fetchLastFiveCycles(): Promise<any[]> {
  const accessToken = getWhoopAccessToken();
  if (!accessToken) {
    console.error('WHOOP access is not configured');
    return [];
  }

  try {
    const response = await fetch(
      `${WHOOP_API_HOSTNAME}/developer/v1/cycle?limit=5`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch cycles. Status:', response.status);
      throw new Error('Failed to fetch cycles');
    }

    const data = await response.json();
    return data.records;
  } catch {
    console.error('Unable to fetch cycle data');
    return [];
  }
}

export async function fetchHeartRateData(): Promise<number> {
  const accessToken = getWhoopAccessToken();
  if (!accessToken) {
    console.error('WHOOP access is not configured');
    return 0;
  }

  try {
    const response = await fetch(
      `${WHOOP_API_HOSTNAME}/developer/v1/cycle/recovery`,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );

    if (!response.ok) {
      console.error('Failed to fetch heart rate data. Status:', response.status);
      throw new Error('Failed to fetch heart rate data');
    }

    const data = await response.json();
    return data.resting_heart_rate;
  } catch {
    console.error('Unable to fetch heart rate data');
    return 0;
  }
}
