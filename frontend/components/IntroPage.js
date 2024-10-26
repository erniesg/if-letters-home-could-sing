'use client'

import React, { useRef, useEffect } from 'react'
import { Canvas, useFrame, extend, useThree } from '@react-three/fiber'
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry'
import { FontLoader } from 'three/examples/jsm/loaders/FontLoader'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

extend({ TextGeometry })

function Text() {
  const mesh = useRef()
  const font = useRef()
  const { scene } = useThree()

  useEffect(() => {
    new FontLoader().load('/fonts/helvetiker_bold.typeface.json', (loadedFont) => {
      font.current = loadedFont
      const textGeometry = new TextGeometry('If Letters Home Could Sing', {
        font: font.current,
        size: 12,
        height: 2,
        curveSegments: 12,
        bevelEnabled: true,
        bevelThickness: 0.5,
        bevelSize: 0.3,
        bevelSegments: 5
      })
      textGeometry.center()
      mesh.current.geometry = textGeometry
    })
  }, [scene])

  useFrame(() => {
    if (mesh.current) {
      mesh.current.rotation.y += 0.005
    }
  })

  return (
    <mesh ref={mesh}>
      <meshPhongMaterial attach="material" color={0xffffff} specular={0xffffff} shininess={100} />
    </mesh>
  )
}

function Particles() {
  const points = useRef()

  useEffect(() => {
    const particleCount = 5000
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)

    for (let i = 0; i < particleCount * 3; i++) {
      positions[i] = (Math.random() - 0.5) * 300
      colors[i] = Math.random()
    }

    points.current.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    points.current.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  }, [])

  useFrame(() => {
    if (points.current) {
      points.current.rotation.x += 0.0005
      points.current.rotation.y += 0.0005
    }
  })

  return (
    <points ref={points}>
      <bufferGeometry />
      <pointsMaterial size={0.5} vertexColors />
    </points>
  )
}

export default function IntroPage() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <Canvas camera={{ position: [0, 0, 200], fov: 75 }}>
        <ambientLight intensity={0.4} />
        <pointLight position={[0, 0, 100]} intensity={1} />
        <Text />
        <Particles />
        <EffectComposer>
          <Bloom luminanceThreshold={0} luminanceSmoothing={0.9} height={300} />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
