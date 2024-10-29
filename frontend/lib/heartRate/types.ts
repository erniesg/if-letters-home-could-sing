export interface HeartRateData {
  currentRate: number;
  timestamp: number;
  movingAverage: number;
}

export interface HeartRateWindow {
  values: number[];
  maxSize: number;
}
