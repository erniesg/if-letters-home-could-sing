export class HeartRateAnalyzer {
  private window: number[];
  private readonly windowSize: number;

  constructor(windowSize: number = 10) {
    this.window = [];
    this.windowSize = windowSize;
  }

  addReading(value: number): void {
    this.window.push(value);
    if (this.window.length > this.windowSize) {
      this.window.shift();
    }
    console.log('Heart Rate Window:', this.window);
  }

  getMovingAverage(): number {
    if (this.window.length === 0) return 0;
    const sum = this.window.reduce((a, b) => a + b, 0);
    return Math.round(sum / this.window.length);
  }
}
