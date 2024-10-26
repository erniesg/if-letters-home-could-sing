"use client"

import { useRef, useEffect, useState, useMemo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Text, OrbitControls, PerspectiveCamera } from '@react-three/drei'
import { useSpring, a } from '@react-spring/three'
import * as THREE from 'three'

function Word({ children, ...props }) {
  const color = new THREE.Color()
  const fontProps = { fontSize: 2.5, letterSpacing: -0.05, lineHeight: 1, 'material-toneMapped': false }
  const ref = useRef()
  const [hovered, setHovered] = useState(false)
  const over = (e) => (e.stopPropagation(), setHovered(true))
  const out = () => setHovered(false)

  // @ts-ignore
  useFrame(({ camera }) => {
    if (ref.current) {
      ref.current.quaternion.copy(camera.quaternion)
      ref.current.material.color.lerp(color.set(hovered ? '#fa2720' : 'white'), 0.1)
    }
  })

  return (
    <Text
      ref={ref}
      onPointerOver={over}
      onPointerOut={out}
      {...props}
      {...fontProps}
    >
      {children}
    </Text>
  )
}

function Particles({ count = 1000 }) {
  const mesh = useRef()
  const light = useRef()
  const { size, viewport } = useThree()
  const aspect = size.width / viewport.width

  const dummy = useMemo(() => new THREE.Object3D(), [])
  const particles = useMemo(() => {
    const temp = []
    for (let i = 0; i < count; i++) {
      const t = Math.random() * 100
      const factor = 20 + Math.random() * 100
      const speed = 0.01 + Math.random() / 200
      const xFactor = -50 + Math.random() * 100
      const yFactor = -50 + Math.random() * 100
      const zFactor = -50 + Math.random() * 100
      temp.push({ t, factor, speed, xFactor, yFactor, zFactor, mx: 0, my: 0 })
    }
    return temp
  }, [count])

  // @ts-ignore
  useFrame((state) => {
    light.current.position.set(state.mouse.x / aspect * 20, state.mouse.y / aspect * 20, 0)
    particles.forEach((particle, i) => {
      let { t, factor, speed, xFactor, yFactor, zFactor } = particle
      t = particle.t += speed / 2
      const a = Math.cos(t) + Math.sin(t * 1) / 10
      const b = Math.sin(t) + Math.cos(t * 2) / 10
      const s = Math.cos(t)
      particle.mx += (state.mouse.x - particle.mx) * 0.01
      particle.my += (state.mouse.y * -1 - particle.my) * 0.01
      dummy.position.set(
        (particle.mx / 10) * a + xFactor + Math.cos((t / 10) * factor) + (Math.sin(t * 1) * factor) / 10,
        (particle.my / 10) * b + yFactor + Math.sin((t / 10) * factor) + (Math.cos(t * 2) * factor) / 10,
        (particle.my / 10) * b + zFactor + Math.cos((t / 10) * factor) + (Math.sin(t * 3) * factor) / 10
      )
      dummy.scale.set(s, s, s)
      dummy.rotation.set(s * 5, s * 5, s * 5)
      dummy.updateMatrix()
      mesh.current.setMatrixAt(i, dummy.matrix)
    })
    mesh.current.instanceMatrix.needsUpdate = true
  })

  return (
    <>
      <pointLight ref={light} distance={40} intensity={8} color="lightblue" />
      <instancedMesh ref={mesh} args={[null, null, count]}>
        <dodecahedronGeometry args={[0.2, 0]} />
        <meshPhongMaterial color="#050505" />
      </instancedMesh>
    </>
  )
}

function Scene({ progress }) {
  const group = useRef()
  const { scale } = useSpring({ scale: progress, config: { mass: 5, tension: 500, friction: 150 } })

  useFrame(() => {
    group.current.position.y = (-1 + progress) * 10
    group.current.rotation.y += 0.01
  })

  return (
    <a.group ref={group} scale={scale}>
      <Word position={[-20, 0, 0]}>If</Word>
      <Word position={[-12, 0, 0]}>Letters</Word>
      <Word position={[0, 0, 0]}>Home</Word>
      <Word position={[15, 0, 0]}>Could</Word>
      <Particles />
    </a.group>
  )
}

export function TextScroll3D() {
  const [progress, setProgress] = useState(0)
  const containerRef = useRef()

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setProgress(entry.intersectionRatio)
      },
      { threshold: new Array(101).fill(0).map((_, i) => i / 100) }
    )

    if (containerRef.current) {
      observer.observe(containerRef.current)
    }

    return () => observer.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="h-[200vh] w-full">
      <div className="sticky top-0 h-screen w-full">
        <Canvas>
          <PerspectiveCamera makeDefault position={[0, 0, 35]} />
          <OrbitControls enableZoom={false} enablePan={false} enableRotate={false} />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} />
          <Scene progress={progress} />
        </Canvas>
      </div>
    </div>
  )
}
