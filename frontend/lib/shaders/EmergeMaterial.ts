import * as THREE from 'three';
import { extend } from '@react-three/fiber';

class EmergeMaterial extends THREE.ShaderMaterial {
  constructor() {
    super({
      uniforms: {
        uTexture: { value: null },
        uProgress: { value: 0 },
        uFillColor: { value: new THREE.Color('#000000') },
        uPixels: { value: [] },
        uTextureSize: { value: new THREE.Vector2(1, 1) },
        uElementSize: { value: new THREE.Vector2(1, 1) },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform sampler2D uTexture;
        uniform float uProgress;
        uniform vec3 uFillColor;
        uniform float uPixels[35];
        uniform vec2 uTextureSize;
        uniform vec2 uElementSize;
        varying vec2 vUv;

        void main() {
          vec2 ratio = vec2(
            min((uElementSize.x / uElementSize.y) / (uTextureSize.x / uTextureSize.y), 1.0),
            min((uElementSize.y / uElementSize.x) / (uTextureSize.y / uTextureSize.x), 1.0)
          );
          vec2 uv = vec2(
            vUv.x * ratio.x + (1.0 - ratio.x) * 0.5,
            vUv.y * ratio.y + (1.0 - ratio.y) * 0.5
          );
          float pixelIndex = floor(uProgress * 35.0);
          float pixels = uPixels[int(pixelIndex)];
          vec2 blocks = vec2(uTextureSize.x * pixels, uTextureSize.y * pixels);
          vec2 newUV = floor(uv * blocks) / blocks;
          vec4 texture = texture2D(uTexture, newUV);
          gl_FragColor = vec4(mix(uFillColor, texture.rgb, uProgress), 1.0);
        }
      `
    });
  }
}

extend({ EmergeMaterial });
