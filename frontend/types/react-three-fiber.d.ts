import type { ThreeElement } from '@react-three/fiber';
import type * as THREE from 'three';


declare class EmergeMaterial extends THREE.ShaderMaterial {
  uFillColor: THREE.Color;
  uProgress: number;
  uType: number;
  uTexture: THREE.Texture | null;
  uPixels: number[];
  uTextureSize: THREE.Vector2;
  uElementSize: THREE.Vector2;
}

declare module '@react-three/fiber' {
  interface ThreeElements {
    emergeMaterial: ThreeElement<typeof EmergeMaterial>;
  }
}
