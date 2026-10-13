import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { HandChoice, HandSkin } from '../types';

interface HandCard3DProps {
  choice: HandChoice | null;
  label: string;
  score: number;
  isPlayer: boolean;
  handSkin: HandSkin;
  isShaking: boolean;
}

export const HandCard3D: React.FC<HandCard3DProps> = ({
  choice,
  label,
  score,
  isPlayer,
  handSkin,
  isShaking
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const handGroupRef = useRef<THREE.Group | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 180;
    const height = container.clientHeight || 200;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x181e29); // Modern clean dark card background matching screenshot

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 50);
    camera.position.set(0, 0.35, 3.6);
    camera.lookAt(0, 0.25, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // Warm, soft studio lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xfff7ed, 2.0);
    keyLight.position.set(2, 4, 3);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xe0f2fe, 1.2);
    fillLight.position.set(-2, 1, 2);
    scene.add(fillLight);

    const rimLight = new THREE.PointLight(
      isPlayer ? new THREE.Color(handSkin.accentColor).getHex() : 0x38bdf8,
      2.0,
      8
    );
    rimLight.position.set(0, 2, -1.5);
    scene.add(rimLight);

    // Hand Group
    const handGroup = new THREE.Group();
    handGroup.position.set(0, -0.65, 0);
    scene.add(handGroup);
    handGroupRef.current = handGroup;

    // Materials
    const palmColorHex = isPlayer ? handSkin.palmColor : '#ffd0b0';
    const sleeveColorHex = isPlayer ? handSkin.sleeveColor : '#ffffff';

    const skinMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(palmColorHex),
      roughness: 0.38,
      metalness: handSkin.id === 'cyber' ? 0.7 : handSkin.id === 'gold' ? 0.85 : 0.08
    });

    const sleeveMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(sleeveColorHex),
      roughness: 0.45,
      metalness: 0.1
    });

    const cuffRimMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(isPlayer ? handSkin.accentColor : '#e2e8f0'),
      roughness: 0.2,
      metalness: 0.5
    });

    // 1. Arm Sleeve / Forearm (pointing straight up)
    const sleeveGeo = new THREE.CylinderGeometry(0.36, 0.4, 0.95, 24);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, sleeveMat);
    sleeveMesh.position.y = 0.35;
    handGroup.add(sleeveMesh);

    // Sleeve Cuff rim
    const cuffGeo = new THREE.TorusGeometry(0.37, 0.035, 16, 32);
    const cuffMesh = new THREE.Mesh(cuffGeo, cuffRimMat);
    cuffMesh.rotation.x = Math.PI / 2;
    cuffMesh.position.y = 0.8;
    handGroup.add(cuffMesh);

    // 2. Wrist
    const wristGeo = new THREE.CylinderGeometry(0.3, 0.32, 0.25, 20);
    const wristMesh = new THREE.Mesh(wristGeo, skinMat);
    wristMesh.position.y = 0.92;
    handGroup.add(wristMesh);

    // 3. Palm Base
    const palmGroup = new THREE.Group();
    palmGroup.position.y = 1.15;
    handGroup.add(palmGroup);

    // We build the gesture meshes based on `choice`
    // Default to Rock if null or during shake
    const currentChoice: HandChoice = choice || 'rock';

    if (currentChoice === 'rock') {
      // --- ROCK: Stylized clean closed fist pointing up ---
      const fistMainGeo = new THREE.BoxGeometry(0.66, 0.55, 0.45);
      const fistMesh = new THREE.Mesh(fistMainGeo, skinMat);
      fistMesh.position.y = 0.15;
      palmGroup.add(fistMesh);

      // Knuckle ridges
      for (let i = 0; i < 4; i++) {
        const kGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.14, 16);
        const kMesh = new THREE.Mesh(kGeo, skinMat);
        kMesh.rotation.x = Math.PI / 2;
        kMesh.position.set(-0.21 + i * 0.14, 0.4, 0.05);
        palmGroup.add(kMesh);

        // Folded finger segments
        const fFoldGeo = new THREE.CylinderGeometry(0.075, 0.075, 0.38, 16);
        const fFoldMesh = new THREE.Mesh(fFoldGeo, skinMat);
        fFoldMesh.rotation.z = Math.PI / 2;
        fFoldMesh.position.set(-0.21 + i * 0.14, 0.22, 0.22);
        palmGroup.add(fFoldMesh);
      }

      // Thumb folded across front
      const thumbGeo = new THREE.CylinderGeometry(0.1, 0.09, 0.48, 16);
      const thumbMesh = new THREE.Mesh(thumbGeo, skinMat);
      thumbMesh.rotation.z = Math.PI / 2.3;
      thumbMesh.rotation.y = -0.2;
      thumbMesh.position.set(-0.02, 0.18, 0.25);
      palmGroup.add(thumbMesh);

      const thumbTipGeo = new THREE.SphereGeometry(0.09, 14, 14);
      const thumbTip = new THREE.Mesh(thumbTipGeo, skinMat);
      thumbTip.position.set(0.2, 0.22, 0.24);
      palmGroup.add(thumbTip);
    } else if (currentChoice === 'paper') {
      // --- PAPER: Open palm pointing straight up with fingers fanned ---
      const palmFlatGeo = new THREE.BoxGeometry(0.64, 0.62, 0.18);
      const palmFlatMesh = new THREE.Mesh(palmFlatGeo, skinMat);
      palmFlatMesh.position.y = 0.15;
      palmGroup.add(palmFlatMesh);

      // 4 Extended fingers
      const fingerLengths = [0.65, 0.76, 0.7, 0.54]; // Index, Middle, Ring, Pinky
      const spreads = [-0.14, -0.04, 0.06, 0.16];

      for (let i = 0; i < 4; i++) {
        const fl = fingerLengths[i];
        const fGeo = new THREE.CylinderGeometry(0.065, 0.075, fl, 16);
        const fMesh = new THREE.Mesh(fGeo, skinMat);
        fMesh.position.set(-0.21 + i * 0.14, 0.45 + fl / 2, 0);
        fMesh.rotation.z = spreads[i];
        palmGroup.add(fMesh);

        // Fingertip cap
        const tipGeo = new THREE.SphereGeometry(0.065, 14, 14);
        const tipMesh = new THREE.Mesh(tipGeo, skinMat);
        tipMesh.position.set(-0.21 + i * 0.14 - Math.sin(spreads[i]) * (fl / 2), 0.45 + fl, 0);
        palmGroup.add(tipMesh);
      }

      // Extended Thumb pointing out
      const thumbGeo = new THREE.CylinderGeometry(0.08, 0.085, 0.48, 16);
      const thumbMesh = new THREE.Mesh(thumbGeo, skinMat);
      thumbMesh.rotation.z = -Math.PI / 3.2;
      thumbMesh.position.set(-0.35, 0.25, 0.04);
      palmGroup.add(thumbMesh);
    } else if (currentChoice === 'scissors') {
      // --- SCISSORS: V-sign (Index & Middle fingers extended, Ring & Pinky & Thumb curled) ---
      const palmVGeo = new THREE.BoxGeometry(0.62, 0.52, 0.32);
      const palmVMesh = new THREE.Mesh(palmVGeo, skinMat);
      palmVMesh.position.y = 0.12;
      palmGroup.add(palmVMesh);

      // Index finger pointing up-left
      const indexLen = 0.82;
      const indexGeo = new THREE.CylinderGeometry(0.07, 0.08, indexLen, 16);
      const indexMesh = new THREE.Mesh(indexGeo, skinMat);
      indexMesh.rotation.z = 0.16;
      indexMesh.position.set(-0.12, 0.42 + indexLen / 2, 0.02);
      palmGroup.add(indexMesh);

      const indexTip = new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 14), skinMat);
      indexTip.position.set(-0.12 - Math.sin(0.16) * (indexLen / 2), 0.42 + indexLen, 0.02);
      palmGroup.add(indexTip);

      // Middle finger pointing up-right (V angle)
      const midLen = 0.86;
      const midGeo = new THREE.CylinderGeometry(0.07, 0.08, midLen, 16);
      const midMesh = new THREE.Mesh(midGeo, skinMat);
      midMesh.rotation.z = -0.16;
      midMesh.position.set(0.12, 0.42 + midLen / 2, 0.02);
      palmGroup.add(midMesh);

      const midTip = new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 14), skinMat);
      midTip.position.set(0.12 - Math.sin(-0.16) * (midLen / 2), 0.42 + midLen, 0.02);
      palmGroup.add(midTip);

      // Curled Ring & Pinky
      for (let i = 2; i < 4; i++) {
        const foldGeo = new THREE.CylinderGeometry(0.07, 0.07, 0.26, 16);
        const foldMesh = new THREE.Mesh(foldGeo, skinMat);
        foldMesh.rotation.z = Math.PI / 2;
        foldMesh.position.set(0.16 + (i - 2) * 0.08, 0.18, 0.18);
        palmGroup.add(foldMesh);
      }

      // Thumb folded over curled fingers
      const thumbGeo = new THREE.CylinderGeometry(0.08, 0.08, 0.42, 16);
      const thumbMesh = new THREE.Mesh(thumbGeo, skinMat);
      thumbMesh.rotation.z = Math.PI / 2.5;
      thumbMesh.position.set(0.05, 0.18, 0.22);
      palmGroup.add(thumbMesh);
    }

    // Render loop
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      if (handGroupRef.current) {
        if (isShaking) {
          // Energetic shake pumping up/down for "Tosh-Qog'oz-Qaychi!"
          handGroupRef.current.position.y = -0.65 + Math.sin(elapsed * 24) * 0.18;
          handGroupRef.current.rotation.z = Math.sin(elapsed * 20) * 0.08;
        } else {
          // Gentle breathing hover
          handGroupRef.current.position.y = -0.65 + Math.sin(elapsed * 2.5) * 0.03;
          handGroupRef.current.rotation.z = 0;
        }
      }

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      renderer.dispose();
      if (container && renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [choice, handSkin, isShaking, isPlayer]);

  return (
    <div className="relative flex flex-col items-center justify-between w-full h-[220px] sm:h-[260px] rounded-3xl bg-[#141923] border border-slate-800/80 shadow-[0_12px_28px_rgba(0,0,0,0.6)] overflow-hidden p-3 select-none">
      {/* 3D Hand Canvas */}
      <div ref={mountRef} className="w-full h-[150px] sm:h-[180px] rounded-2xl overflow-hidden" />

      {/* Card Footer Labels */}
      <div className="w-full text-center mt-1">
        <h3 className="text-sm sm:text-base font-extrabold text-slate-100 tracking-wide">
          {label}
        </h3>
        <p className="text-xs font-semibold text-slate-400">
          {score} ochko
        </p>
      </div>

      {/* Player Skin Indicator Badge */}
      {isPlayer && (
        <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-full bg-slate-900/80 border border-slate-700/80 text-[10px] font-bold text-slate-300 flex items-center gap-1">
          <span>{handSkin.icon}</span>
          <span className="hidden sm:inline">{handSkin.name}</span>
        </div>
      )}
    </div>
  );
};
