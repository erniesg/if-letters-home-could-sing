'use client'

import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import * as d3 from 'd3-force'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import gsap from 'gsap'

// Mock data for letters (expanded for better clustering demonstration)
const letters = [
  { id: 1, text: 'Dear John...', artist: 'Jane Doe', date: '1920', material: 'Paper', dimensions: '10x15cm', prominence: 0.8 },
  { id: 2, text: 'To whom it may concern...', artist: 'John Smith', date: '1935', material: 'Parchment', dimensions: '12x18cm', prominence: 0.6 },
  { id: 3, text: 'My dearest friend...', artist: 'Emily Brown', date: '1922', material: 'Paper', dimensions: '10x15cm', prominence: 0.9 },
  { id: 4, text: 'Greetings from afar...', artist: 'William Johnson', date: '1940', material: 'Cardstock', dimensions: '15x20cm', prominence: 0.7 },
  { id: 5, text: 'In regards to your inquiry...', artist: 'Sarah Davis', date: '1933', material: 'Paper', dimensions: '11x17cm', prominence: 0.5 },
  // Add more letters as needed
]

const LetterClusterVisualization: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scene, setScene] = useState<THREE.Scene | null>(null)
  const [camera, setCamera] = useState<THREE.PerspectiveCamera | null>(null)
  const [renderer, setRenderer] = useState<THREE.WebGLRenderer | null>(null)
  const [controls, setControls] = useState<OrbitControls | null>(null)
  const [bpm, setBpm] = useState<number>(60)
  const [selectedLetter, setSelectedLetter] = useState<any | null>(null)
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false)
  const [highlightedLetters, setHighlightedLetters] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!containerRef.current) return

    // Set up Three.js scene
    const newScene = new THREE.Scene()
    const newCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000)
    const newRenderer = new THREE.WebGLRenderer()

    newRenderer.setSize(window.innerWidth, window.innerHeight)
    containerRef.current.appendChild(newRenderer.domElement)

    const newControls = new OrbitControls(newCamera, newRenderer.domElement)
    newCamera.position.z = 50

    setScene(newScene)
    setCamera(newCamera)
    setRenderer(newRenderer)
    setControls(newControls)

    // Clean up
    return () => {
      newRenderer.dispose()
      if (containerRef.current) {
        containerRef.current.removeChild(newRenderer.domElement)
      }
    }
  }, [])

  useEffect(() => {
    if (!scene || !camera || !renderer || !controls) return

    // Create force simulation
    const simulation = d3.forceSimulation(letters)
      .force('charge', d3.forceManyBody().strength(-20))
      .force('center', d3.forceCenter(0, 0))
      .force('collision', d3.forceCollide().radius(3))
      .force('link', d3.forceLink().id((d: any) => d.id)
        .links(createLinks())
        .distance(30))

    // Create 3D objects for letters
    const letterObjects = letters.map(letter => {
      const geometry = new THREE.SphereGeometry(1, 32, 32)
      const material = new THREE.MeshPhongMaterial({ color: getColorFromMetadata(letter) })
      const sphere = new THREE.Mesh(geometry, material)
      sphere.userData = { letter }
      scene.add(sphere)
      return sphere
    })

    // Add ambient light and directional light
    const ambientLight = new THREE.AmbientLight(0x404040)
    scene.add(ambientLight)
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5)
    directionalLight.position.set(1, 1, 1)
    scene.add(directionalLight)

    // Update positions and sizes based on force simulation and BPM
    simulation.on('tick', () => {
      letterObjects.forEach((obj, i) => {
        const letter = letters[i] as any
        obj.position.set(letter.x!, letter.y!, letter.z || 0)
        const baseScale = 1 + (letter.prominence * 2)
        const bpmScale = highlightedLetters.has(letter.id) ? 1 + (bpm - 60) / 60 : 1
        obj.scale.setScalar(baseScale * bpmScale)
      })
    })

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }

    animate()

    // Handle window resize
    const handleResize = () => {
      if (!camera || !renderer) return
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }

    window.addEventListener('resize', handleResize)

    // Handle key presses for navigation
    const handleKeyPress = (event: KeyboardEvent) => {
      if (!camera) return
      const speed = 1
      switch (event.key) {
        case 'ArrowUp':
          camera.position.y += speed
          break
        case 'ArrowDown':
          camera.position.y -= speed
          break
        case 'ArrowLeft':
          camera.position.x -= speed
          break
        case 'ArrowRight':
          camera.position.x += speed
          break
      }
    }

    window.addEventListener('keydown', handleKeyPress)

    // Handle clicks on letters
    const handleClick = (event: MouseEvent) => {
      if (!camera || !scene || !renderer) return

      const raycaster = new THREE.Raycaster()
      const mouse = new THREE.Vector2()

      mouse.x = (event.clientX / window.innerWidth) * 2 - 1
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1

      raycaster.setFromCamera(mouse, camera)

      const intersects = raycaster.intersectObjects(scene.children)

      if (intersects.length > 0) {
        const selectedObject = intersects[0].object
        if (selectedObject.userData && selectedObject.userData.letter) {
          setSelectedLetter(selectedObject.userData.letter)
          setIsModalOpen(true)
        }
      }
    }

    renderer.domElement.addEventListener('click', handleClick)

    // Handle navigation and letter highlighting
    const handleNavigation = () => {
      const cameraPosition = new THREE.Vector3()
      camera.getWorldPosition(cameraPosition)

      const newHighlightedLetters = new Set<number>()
      letterObjects.forEach(obj => {
        const distance = cameraPosition.distanceTo(obj.position)
        if (distance < 20) {
          newHighlightedLetters.add(obj.userData.letter.id)
          if (!highlightedLetters.has(obj.userData.letter.id)) {
            // Fade in letter content
            const textSprite = createTextSprite(obj.userData.letter.text)
            textSprite.position.copy(obj.position)
            textSprite.position.y += 2
            scene.add(textSprite)
            gsap.from(textSprite.material, { opacity: 0, duration: 1 })
          }
        }
      })
      setHighlightedLetters(newHighlightedLetters)
    }

    controls.addEventListener('change', handleNavigation)

    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('keydown', handleKeyPress)
      renderer.domElement.removeEventListener('click', handleClick)
      controls.removeEventListener('change', handleNavigation)
      simulation.stop()
    }
  }, [scene, camera, renderer, controls, bpm, highlightedLetters])

  // Simulate changing BPM (replace this with actual BPM data from Whoop)
  useEffect(() => {
    const interval = setInterval(() => {
      setBpm(Math.floor(Math.random() * (100 - 60 + 1) + 60))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div>
      <div ref={containerRef} style={{ width: '100vw', height: '100vh' }} />
      <div style={{ position: 'absolute', top: 10, left: 10, color: 'white' }}>
        Current BPM: {bpm}
      </div>
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedLetter?.artist}</DialogTitle>
            <DialogDescription>
              Date: {selectedLetter?.date}<br />
              Material: {selectedLetter?.material}<br />
              Dimensions: {selectedLetter?.dimensions}
            </DialogDescription>
          </DialogHeader>
          <p>{selectedLetter?.text}</p>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// Helper function to create links between similar letters
function createLinks() {
  const links = []
  for (let i = 0; i < letters.length; i++) {
    for (let j = i + 1; j < letters.length; j++) {
      if (areSimilar(letters[i], letters[j])) {
        links.push({ source: letters[i].id, target: letters[j].id })
      }
    }
  }
  return links
}

// Helper function to determine if two letters are similar
function areSimilar(letter1: any, letter2: any) {
  return letter1.material === letter2.material ||
         Math.abs(parseInt(letter1.date) - parseInt(letter2.date)) <= 5 ||
         letter1.dimensions === letter2.dimensions
}

// Helper function to generate color based on letter metadata
function getColorFromMetadata(letter: any) {
  const hue = parseInt(letter.date) % 360
  const saturation = letter.material === 'Paper' ? 70 : 100
  const lightness = letter.dimensions.split('x')[0] > 12 ? 50 : 30
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`
}

// Helper function to create text sprite for letter content
function createTextSprite(text: string) {
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')!
  context.font = 'Bold 20px Arial'
  context.fillStyle = 'rgba(255,255,255,0.95)'
  context.fillText(text, 0, 20)

  const texture = new THREE.Texture(canvas)
  texture.needsUpdate = true

  const spriteMaterial = new THREE.SpriteMaterial({ map: texture })
  return new THREE.Sprite(spriteMaterial)
}

export default LetterClusterVisualization
