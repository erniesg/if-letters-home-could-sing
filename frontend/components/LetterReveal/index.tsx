'use client';

import { useState, useEffect, useLayoutEffect, useRef, type ComponentProps } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import * as THREE from 'three';
import useScreenSize from '../../lib/stuff/useScreenSize';
import { View } from '@react-three/drei';
import { useControls } from 'leva';
import '../../lib/stuff/EmergeMaterial';

// Rest of your component remains the same

const PIXELS =  [1, 1.5, 2, 2.5, 3, 1, 1.5, 2, 2.5, 3, 3.5, 4, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 20, 100].map((v) => v/100)


type EmergeMaterial = THREE.ShaderMaterial & {
  uProgress: number;
  uType: number;
};

type EmergeMesh = THREE.Mesh<THREE.BufferGeometry, EmergeMaterial>;

type LetterRevealProps = ComponentProps<typeof View> & {
  url: string;
  type: number;
  isVisible?: boolean;
};

export default function LetterReveal({ url, type, isVisible: _isVisible, ...viewProps }: LetterRevealProps) {

    const { fillColor } = useControls({ fillColor: '#403fb7', })

    const [refMesh, setRefMesh] = useState<EmergeMesh | null>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [textureSize, setTextureSize] = useState<[number, number]>([0, 0]);
    const [elementSize, setElementSize] = useState<[number, number]>([0, 0]);
    const ref = useRef<HTMLElement | THREE.Group>(null);
    const screenSize = useScreenSize();
    const [isIntersecting, setIsIntersecting] = useState(false);

    useEffect(() => {
      new THREE.TextureLoader().loadAsync(url).then((data) => {
        // data.colorSpace = THREE.LinearSRGBColorSpace;
        setTextureSize([data.source.data.width, data.source.data.height]);
        setTexture(data);
      });
    }, [url]);

    useEffect(() => {

      if(refMesh) {
        refMesh.material.uProgress = 0
        refMesh.material.uType = type
      }
    },[refMesh, type])

    useGSAP(() => {
      if (refMesh?.material) {
        gsap.to(refMesh.material, {
          uProgress: isIntersecting ? 1 : 0,
          duration: 1.5,
          ease: "none",
        });
      }
    }, [isIntersecting, type]);

    // scroll check
    // only set intersecting if refMesh is available, important
    // Thanks Cody Bennett for this issue!
    useLayoutEffect(() => {
      const element = ref.current;
      if (refMesh && element instanceof HTMLElement) {
        const bounds = element.getBoundingClientRect();
        setElementSize([bounds.width, bounds.height]);
        refMesh.scale.set(bounds.width, bounds.height, 1);
        const observer = new IntersectionObserver(([entry]) => {
          setIsIntersecting(entry.isIntersecting);
        });
        observer.observe(element);
        return () => observer.disconnect();
      }
    }, [refMesh]);

    // resize
    useEffect(() => {
      const element = ref.current;
      if (refMesh && element instanceof HTMLElement) {
        const bounds = element.getBoundingClientRect();
        setElementSize([bounds.width, bounds.height]);
        refMesh.scale.set(bounds.width, bounds.height, 1);
      }
    }, [refMesh, screenSize]);

    return (
      <View {...viewProps} ref={ref}>
        <mesh ref={(mesh) => setRefMesh(mesh as EmergeMesh | null)}>
          <emergeMaterial
            uFillColor={new THREE.Color(fillColor)}
            transparent={true}
            uTexture={texture}
            uPixels={PIXELS}
            uTextureSize={new THREE.Vector2(textureSize[0], textureSize[1])}
            uElementSize={new THREE.Vector2(elementSize[0], elementSize[1])}
          />
          <planeGeometry args={[1, 1]} />
        </mesh>
      </View>
    );
  }
