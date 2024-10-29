export interface AudioInitializerProps {
  onHeartRateUpdate: (rate: number) => void;
  onInitialized: (isInitialized: boolean) => void;
}

export interface InitializerStatus {
  ble: 'idle' | 'connecting' | 'connected' | 'error';
  audio: 'idle' | 'loading' | 'ready' | 'error';
}
