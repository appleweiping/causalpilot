"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { EpisodeSnapshot, MissionSegment } from "@/lib/types";

interface MarketSceneProps {
  snapshot: EpisodeSnapshot;
  phaseIndex: number;
  reducedMotion: boolean;
}

function mulberry32(seed: number) {
  return () => {
    let value = (seed += 0x6d2b79f5);
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function visualColor(segment: MissionSegment): string {
  if (segment.status === "eligible") return "#66f5bf";
  if (segment.status === "abstain") return "#f3a45f";
  if (segment.status === "paused" || segment.risk >= 0.74) return "#ff5e68";
  if (segment.risk >= 0.48) return "#f2c15d";
  return "#56d9f5";
}

function ClusterCloud({ segment, reducedMotion }: { segment: MissionSegment; reducedMotion: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const count = Math.max(20, Math.round(segment.share * 150));
  const positions = useMemo(() => {
    const random = mulberry32(
      segment.id.split("").reduce((total, char) => total + char.charCodeAt(0), 23),
    );
    const buffer = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const radius = 0.28 + Math.pow(random(), 0.62) * (0.58 + segment.share);
      const theta = random() * Math.PI * 2;
      const phi = Math.acos(2 * random() - 1);
      buffer[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
      buffer[index * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.7;
      buffer[index * 3 + 2] = radius * Math.cos(phi) * 0.72;
    }
    return buffer;
  }, [count, segment.id, segment.share]);
  const color = visualColor(segment);
  const nodeScale = 0.28 + segment.share * 1.1;

  useFrame(({ clock }, delta) => {
    if (!groupRef.current || reducedMotion) return;
    groupRef.current.rotation.y += delta * 0.06;
    const pulse = 1 + Math.sin(clock.elapsedTime * 1.3 + segment.share * 10) * 0.022;
    groupRef.current.scale.setScalar(pulse);
  });

  return (
    <group ref={groupRef} position={segment.coordinates}>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial color={color} size={0.045} transparent opacity={0.72} sizeAttenuation depthWrite={false} />
      </points>

      <mesh scale={nodeScale}>
        <icosahedronGeometry args={[1, 2]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.75}
          roughness={0.3}
          metalness={0.35}
          transparent
          opacity={0.72}
          wireframe={segment.status === "paused"}
        />
      </mesh>

      <mesh scale={nodeScale * (1.45 + segment.risk * 0.55)}>
        <sphereGeometry args={[1, 24, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.045 + segment.risk * 0.1}
          wireframe
          depthWrite={false}
        />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]} scale={nodeScale * 1.7}>
        <torusGeometry args={[1, 0.012, 8, 64]} />
        <meshBasicMaterial color={color} transparent opacity={0.48} depthWrite={false} />
      </mesh>

    </group>
  );
}

function FlowParticle({
  segment,
  offset,
  phaseIndex,
  reducedMotion,
}: {
  segment: MissionSegment;
  offset: number;
  phaseIndex: number;
  reducedMotion: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const curve = useMemo(() => {
    const destination = new THREE.Vector3(...segment.coordinates);
    const midpoint = destination.clone().multiplyScalar(0.5);
    midpoint.z += 0.7;
    midpoint.y += segment.coordinates[0] * 0.08;
    return new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, 0, 0), midpoint, destination);
  }, [segment.coordinates]);
  const color = visualColor(segment);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const time = reducedMotion ? offset : (clock.elapsedTime * (0.12 + segment.share * 0.18) + offset) % 1;
    ref.current.position.copy(curve.getPoint(time));
    ref.current.visible = phaseIndex >= 2;
  });

  return (
    <mesh ref={ref} visible={phaseIndex >= 2}>
      <sphereGeometry args={[0.035, 8, 8]} />
      <meshBasicMaterial color={color} transparent opacity={0.85} toneMapped={false} />
    </mesh>
  );
}

function CausalLink({
  segment,
  phaseIndex,
  reducedMotion,
}: {
  segment: MissionSegment;
  phaseIndex: number;
  reducedMotion: boolean;
}) {
  const destination = new THREE.Vector3(...segment.coordinates);
  const midpoint = destination.clone().multiplyScalar(0.5);
  midpoint.z += 0.7;
  midpoint.y += segment.coordinates[0] * 0.08;
  const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, 0, 0), midpoint, destination);
  const points = useMemo(() => {
    const values = curve.getPoints(28);
    const positions = new Float32Array(values.length * 3);
    values.forEach((point, index) => {
      positions[index * 3] = point.x;
      positions[index * 3 + 1] = point.y;
      positions[index * 3 + 2] = point.z;
    });
    return positions;
  }, [curve]);
  const color = visualColor(segment);

  return (
    <>
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[points, 3]} />
        </bufferGeometry>
        <lineBasicMaterial
          color={color}
          transparent
          opacity={phaseIndex < 1 ? 0.12 : 0.38}
          depthWrite={false}
        />
      </line>
      {[0.05, 0.3, 0.55, 0.8].map((offset) => (
        <FlowParticle
          key={`${segment.id}-${offset}`}
          segment={segment}
          offset={offset}
          phaseIndex={phaseIndex}
          reducedMotion={reducedMotion}
        />
      ))}
    </>
  );
}

function PolicyCore({ phaseIndex }: { phaseIndex: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.y = clock.elapsedTime * 0.16;
    ref.current.rotation.x = Math.sin(clock.elapsedTime * 0.21) * 0.08;
  });
  const color = phaseIndex === 3 || phaseIndex === 4 ? "#ffb85c" : "#61e7f6";

  return (
    <group ref={ref}>
      <mesh scale={0.42}>
        <octahedronGeometry args={[1, 1]} />
        <meshStandardMaterial
          color="#07151b"
          emissive={color}
          emissiveIntensity={1.4}
          metalness={0.8}
          roughness={0.25}
        />
      </mesh>
      {[0.62, 0.82, 1.04].map((scale, index) => (
        <mesh key={scale} rotation={[Math.PI / 2 + index * 0.32, index * 0.5, 0]} scale={scale}>
          <torusGeometry args={[1, 0.016, 8, 64]} />
          <meshBasicMaterial color={color} transparent opacity={0.62 - index * 0.14} depthWrite={false} />
        </mesh>
      ))}
      <pointLight color={color} intensity={5} distance={5} />
    </group>
  );
}

function DriftShockwave({ active, reducedMotion }: { active: boolean; reducedMotion: boolean }) {
  const mesh = useRef<THREE.Mesh>(null);
  const material = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!mesh.current || !material.current || !active) return;
    const cycle = reducedMotion ? 0.7 : (clock.elapsedTime * 0.34) % 1;
    mesh.current.scale.setScalar(0.8 + cycle * 4.2);
    material.current.opacity = 0.38 * (1 - cycle);
  });

  if (!active) return null;
  return (
    <mesh ref={mesh} position={[2.35, -1.25, 0.25]} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[0.55, 0.018, 8, 64]} />
      <meshBasicMaterial ref={material} color="#ff5967" transparent opacity={0.3} depthWrite={false} />
    </mesh>
  );
}

function StarField() {
  const points = useMemo(() => {
    const random = mulberry32(4242);
    const positions = new Float32Array(270);
    for (let index = 0; index < positions.length; index += 3) {
      positions[index] = (random() - 0.5) * 14;
      positions[index + 1] = (random() - 0.5) * 9;
      positions[index + 2] = -2 - random() * 5;
    }
    return positions;
  }, []);
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#6f9eaa" size={0.016} transparent opacity={0.45} sizeAttenuation />
    </points>
  );
}

function CameraRig({ phaseIndex, reducedMotion }: { phaseIndex: number; reducedMotion: boolean }) {
  const { camera } = useThree();
  const targets = useMemo(
    () => [
      new THREE.Vector3(0, 0.15, 8.2),
      new THREE.Vector3(-0.35, 0.15, 7.5),
      new THREE.Vector3(0.2, 0.05, 6.9),
      new THREE.Vector3(0.9, -0.35, 7.1),
      new THREE.Vector3(0.4, 0.1, 7.4),
      new THREE.Vector3(0, 0.05, 6.7),
    ],
    [],
  );

  useLayoutEffect(() => {
    if (!reducedMotion) return;
    camera.position.copy(targets[phaseIndex]);
    camera.lookAt(0, 0, 0);
  }, [camera, phaseIndex, reducedMotion, targets]);

  useFrame(() => {
    if (reducedMotion) return;
    camera.position.lerp(targets[phaseIndex], 0.018);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

function Network({ snapshot, phaseIndex, reducedMotion }: MarketSceneProps) {
  return (
    <>
      <color attach="background" args={["#05090c"]} />
      <fog attach="fog" args={["#05090c", 7, 14]} />
      <ambientLight intensity={0.8} />
      <directionalLight position={[3, 4, 5]} intensity={1.2} color="#9ee9f5" />
      <pointLight position={[-4, -2, 3]} intensity={2} color="#edb55d" distance={7} />
      <CameraRig phaseIndex={phaseIndex} reducedMotion={reducedMotion} />
      <StarField />
      <gridHelper args={[12, 24, "#17343c", "#10252c"]} position={[0, -2.55, -0.5]} />
      <PolicyCore phaseIndex={phaseIndex} />
      {snapshot.segments.map((segment) => (
        <group key={segment.id}>
          <CausalLink segment={segment} phaseIndex={phaseIndex} reducedMotion={reducedMotion} />
          <ClusterCloud segment={segment} reducedMotion={reducedMotion} />
        </group>
      ))}
      <DriftShockwave active={phaseIndex === 3 || phaseIndex === 4} reducedMotion={reducedMotion} />
    </>
  );
}

export function MarketScene(props: MarketSceneProps) {
  const segmentSummary = props.snapshot.segments
    .map((segment) => `${segment.label}: ${Math.round(segment.share * 100)}%, ${segment.status}`)
    .join("; ");

  return (
    <div className="market-scene">
      <Canvas
        dpr={[1, 1.55]}
        camera={{ position: [0, 0.15, 8.2], fov: 43, near: 0.1, far: 100 }}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
        frameloop={props.reducedMotion ? "demand" : "always"}
        role="img"
        aria-label={`Market topology. ${segmentSummary}`}
      >
        <Network {...props} />
      </Canvas>
      <div className="cluster-label-layer" aria-hidden="true">
        {props.snapshot.segments.map((segment) => {
          const left = 50 + segment.coordinates[0] * 13;
          const top = 50 - segment.coordinates[1] * 16;
          return (
            <div
              className="cluster-label"
              key={segment.id}
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              <span className="cluster-label__index">{String(Math.round(segment.share * 100)).padStart(2, "0")}%</span>
              <span>{segment.label}</span>
              <em>{segment.status}</em>
            </div>
          );
        })}
      </div>
      <p className="sr-only">
        Interactive 3D market topology. Node size encodes cohort share, color and halo encode risk,
        particles encode experimental traffic, and curved links encode decision dependencies.
      </p>
    </div>
  );
}
