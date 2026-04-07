import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

function AnimatedSphere() {
  const meshRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.003;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
  });

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={meshRef}>
        <Sphere args={[2.2, 64, 64]}>
          <MeshDistortMaterial
            color="#1A1A2E"
            roughness={0.4}
            metalness={0.8}
            distort={0.25}
            speed={1.5}
            transparent
            opacity={0.85}
          />
        </Sphere>
      </mesh>
    </Float>
  );
}

function ParticleField() {
  const pointsRef = useRef();
  const count = 200;
  
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 12;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 12;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;
    }
    return pos;
  }, []);

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += 0.0005;
      pointsRef.current.rotation.x += 0.0002;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={count}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#64748B"
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

function OrbitRing({ radius, speed, color, opacity }) {
  const ringRef = useRef();
  
  useFrame((state) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += speed;
    }
  });

  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, 0.008, 16, 100]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} />
    </mesh>
  );
}

function ScaleOfJustice() {
  const groupRef = useRef();
  
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.005;
      // Subtle tilt
      groupRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.5) * 0.05;
    }
  });

  return (
    <Float speed={1} rotationIntensity={0.1} floatIntensity={0.3}>
      <group ref={groupRef}>
        {/* Central pillar */}
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.03, 0.04, 3, 16]} />
          <meshStandardMaterial color="#1A1A2E" roughness={0.3} metalness={0.8} />
        </mesh>
        
        {/* Top beam */}
        <mesh position={[0, 1.5, 0]}>
          <boxGeometry args={[3, 0.04, 0.04]} />
          <meshStandardMaterial color="#1A1A2E" roughness={0.3} metalness={0.8} />
        </mesh>
        
        {/* Left pan chain */}
        <mesh position={[-1.4, 1.1, 0]}>
          <cylinderGeometry args={[0.01, 0.01, 0.8, 8]} />
          <meshStandardMaterial color="#4A4A4A" roughness={0.5} metalness={0.6} />
        </mesh>
        
        {/* Right pan chain */}
        <mesh position={[1.4, 0.9, 0]}>
          <cylinderGeometry args={[0.01, 0.01, 1.2, 8]} />
          <meshStandardMaterial color="#4A4A4A" roughness={0.5} metalness={0.6} />
        </mesh>
        
        {/* Left pan */}
        <mesh position={[-1.4, 0.65, 0]}>
          <cylinderGeometry args={[0.5, 0.5, 0.05, 32]} />
          <meshStandardMaterial color="#2D2D5E" roughness={0.2} metalness={0.9} />
        </mesh>
        
        {/* Right pan */}
        <mesh position={[1.4, 0.25, 0]}>
          <cylinderGeometry args={[0.5, 0.5, 0.05, 32]} />
          <meshStandardMaterial color="#2D2D5E" roughness={0.2} metalness={0.9} />
        </mesh>
        
        {/* Base */}
        <mesh position={[0, -1.5, 0]}>
          <cylinderGeometry args={[0.6, 0.8, 0.1, 32]} />
          <meshStandardMaterial color="#1A1A2E" roughness={0.2} metalness={0.9} />
        </mesh>
      </group>
    </Float>
  );
}

export default function LegalGlobe() {
  return (
    <div className="canvas-container" style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [0, 0, 6], fov: 50 }}
        style={{ background: 'transparent' }}
        dpr={[1, 2]}
        gl={{ alpha: true, antialias: true }}
      >
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 5, 5]} intensity={1} color="#ffffff" />
        <directionalLight position={[-3, 3, 2]} intensity={0.3} color="#E2E8F0" />
        <pointLight position={[0, 2, 3]} intensity={0.5} color="#1A1A2E" />
        
        <ScaleOfJustice />
        <ParticleField />
        
        <OrbitRing radius={3} speed={0.001} color="#1A1A2E" opacity={0.15} />
        <OrbitRing radius={3.5} speed={-0.0008} color="#64748B" opacity={0.1} />
        <OrbitRing radius={4} speed={0.0006} color="#CBD5E1" opacity={0.08} />
      </Canvas>
    </div>
  );
}
