import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { FontLoader } from 'three/examples/jsm/loaders/FontLoader';
import { TextGeometry } from 'three/examples/jsm/geometries/TextGeometry';

const InteractiveText: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.set(0, 0, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x021119);
    containerRef.current.appendChild(renderer.domElement);

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-200, 200);

    let particles: THREE.Points;
    let geometryCopy: THREE.BufferGeometry;

    const createText = (font: THREE.Font) => {
      const textGeometry = new TextGeometry('If Letters Home Could', {
        font: font,
        size: 16,
        height: 0.1,
        curveSegments: 12,
        bevelEnabled: false,
      });

      textGeometry.center();

      const textMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const textMesh = new THREE.Mesh(textGeometry, textMaterial);
      scene.add(textMesh);

      const sampler = new THREE.MeshSurfaceSampler(textMesh).build();
      const particleCount = 50000;
      const particleGeometry = new THREE.BufferGeometry();
      const particlePositions = new Float32Array(particleCount * 3);
      const particleSizes = new Float32Array(particleCount);

      for (let i = 0; i < particleCount; i++) {
        const tempPosition = new THREE.Vector3();
        sampler.sample(tempPosition);
        particlePositions.set([tempPosition.x, tempPosition.y, tempPosition.z], i * 3);
        particleSizes[i] = 0.1;
      }

      particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
      particleGeometry.setAttribute('size', new THREE.BufferAttribute(particleSizes, 1));

      const particleMaterial = new THREE.ShaderMaterial({
        uniforms: {
          color: { value: new THREE.Color(0xffffff) },
          pointTexture: { value: new THREE.TextureLoader().load('https://res.cloudinary.com/dfvtkoboz/image/upload/v1605013866/particle_a64uzf.png') }
        },
        vertexShader: `
          attribute float size;
          varying vec3 vColor;
          void main() {
            vColor = color;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = size * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform vec3 color;
          uniform sampler2D pointTexture;
          varying vec3 vColor;
          void main() {
            gl_FragColor = vec4(color * vColor, 1.0);
            gl_FragColor = gl_FragColor * texture2D(pointTexture, gl_PointCoord);
          }
        `,
        blending: THREE.AdditiveBlending,
        depthTest: false,
        transparent: true,
      });

      particles = new THREE.Points(particleGeometry, particleMaterial);
      scene.add(particles);

      geometryCopy = particleGeometry.clone();
    };

    const loader = new FontLoader();
    loader.load('https://res.cloudinary.com/dydre7amr/raw/upload/v1612950355/font_zsd4dr.json', (font) => {
      createText(font);
      animate();
    });

    const animate = () => {
      requestAnimationFrame(animate);

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObject(particles);

      if (intersects.length > 0) {
        const positions = particles.geometry.attributes.position.array as Float32Array;
        const sizes = particles.geometry.attributes.size.array as Float32Array;
        const initialPositions = geometryCopy.attributes.position.array as Float32Array;

        for (let i = 0; i < positions.length; i += 3) {
          const dx = mouse.x - positions[i];
          const dy = mouse.y - positions[i + 1];
          const distance = Math.sqrt(dx * dx + dy * dy);
          const maxDistance = 10;

          if (distance < maxDistance) {
            positions[i] += (initialPositions[i] - positions[i]) * 0.05;
            positions[i + 1] += (initialPositions[i + 1] - positions[i + 1]) * 0.05;
            sizes[i / 3] = 0.1 + (maxDistance - distance) / maxDistance * 0.5;
          } else {
            positions[i] += (initialPositions[i] - positions[i]) * 0.1;
            positions[i + 1] += (initialPositions[i + 1] - positions[i + 1]) * 0.1;
            sizes[i / 3] = 0.1;
          }
        }

        particles.geometry.attributes.position.needsUpdate = true;
        particles.geometry.attributes.size.needsUpdate = true;
      }

      renderer.render(scene, camera);
    };

    const handleMouseMove = (event: MouseEvent) => {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <>
      <div ref={containerRef} id="magic" style={{ position: 'fixed', width: '100%', height: '100vh', top: 0, left: 0, zIndex: -9999 }} />
      <div className="playground" style={{ position: 'fixed', width: '100%', height: '100vh', top: 0, left: 0, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center' }}>
        <div className="bottomPosition" style={{ textAlign: 'center', marginBottom: '50px' }}>
          <h1 className="special">If Letters Home Could<br /><span className="minText" style={{ fontSize: '14px' }}>Interactive Text</span></h1>
        </div>
      </div>
    </>
  );
};

export default InteractiveText;
