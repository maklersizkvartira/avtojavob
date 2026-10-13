import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { HandChoice, GamePhase, RoundOutcome } from '../types';

interface HandArena3DProps {
  playerChoice: HandChoice | null;
  opponentChoice: HandChoice | null;
  phase: GamePhase;
  countdownStep: number;
  roundOutcome: RoundOutcome | null;
}

interface FingerBones {
  joint1: THREE.Group;
  joint2: THREE.Group;
  joint3: THREE.Group;
}

interface HandRig {
  root: THREE.Group;
  armGroup: THREE.Group;
  wristGroup: THREE.Group;
  palmGroup: THREE.Group;
  thumb: FingerBones;
  index: FingerBones;
  middle: FingerBones;
  ring: FingerBones;
  pinky: FingerBones;
  isPlayer: boolean;
  baseX: number;
  targetPos: THREE.Vector3;
  targetRot: THREE.Euler;
  currentGesture: HandChoice | 'idle' | 'countdown';
}

export const HandArena3D: React.FC<HandArena3DProps> = ({
  playerChoice,
  opponentChoice,
  phase,
  countdownStep,
  roundOutcome
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  // References for render loop
  const rigPlayerRef = useRef<HandRig | null>(null);
  const rigOpponentRef = useRef<HandRig | null>(null);
  const impactParticlesRef = useRef<THREE.Points | null>(null);
  const cameraShakeRef = useRef<number>(0);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // --- SCENE SETUP ---
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080918);
    scene.fog = new THREE.FogExp2(0x080918, 0.045);

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 450;
    const aspect = width / height;

    const camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
    const updateCameraPos = () => {
      const curAspect = (container.clientWidth || window.innerWidth) / (container.clientHeight || 450);
      if (curAspect < 1.0) {
        // Mobile portrait: pull back and raise slightly
        camera.position.set(0, 1.4, 8.2);
        camera.lookAt(0, -0.2, 0);
      } else {
        // Desktop / landscape
        camera.position.set(0, 0.9, 6.2);
        camera.lookAt(0, 0, 0);
      }
    };
    updateCameraPos();

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // --- LIGHTING ---
    const ambientLight = new THREE.AmbientLight(0x202444, 1.2);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
    dirLight.position.set(0, 8, 5);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.bias = -0.0005;
    scene.add(dirLight);

    // Player Neon Rim Light (Cyan)
    const playerLight = new THREE.PointLight(0x00e5ff, 3.5, 12);
    playerLight.position.set(-4, 2, 2);
    scene.add(playerLight);

    // Opponent Neon Rim Light (Amber / Fiery Orange)
    const opponentLight = new THREE.PointLight(0xff7700, 3.5, 12);
    opponentLight.position.set(4, 2, 2);
    scene.add(opponentLight);

    // Center Stage Glow
    const centerSpot = new THREE.SpotLight(0xa855f7, 2.0, 10, Math.PI / 4, 0.4);
    centerSpot.position.set(0, 4, 0);
    centerSpot.target.position.set(0, 0, 0);
    scene.add(centerSpot);
    scene.add(centerSpot.target);

    // --- ARENA FLOOR & PLATFORM ---
    const floorGeo = new THREE.PlaneGeometry(30, 30);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x070814,
      roughness: 0.35,
      metalness: 0.7
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -1.6;
    floor.receiveShadow = true;
    scene.add(floor);

    // Glowing Arena Hologram Rings
    const ringGroup = new THREE.Group();
    ringGroup.position.y = -1.58;

    const createRing = (radius: number, color: number, emissive: number) => {
      const ringGeo = new THREE.RingGeometry(radius - 0.04, radius + 0.04, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.65
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.x = -Math.PI / 2;
      return ringMesh;
    };

    const ring1 = createRing(1.8, 0x00e5ff, 0x00e5ff);
    const ring2 = createRing(2.7, 0xff7700, 0xff7700);
    const ring3 = createRing(3.6, 0xa855f7, 0xa855f7);
    ringGroup.add(ring1, ring2, ring3);
    scene.add(ringGroup);

    // Floating Stardust Particles
    const dustCount = 80;
    const dustGeo = new THREE.BufferGeometry();
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount * 3; i += 3) {
      dustPos[i] = (Math.random() - 0.5) * 12;
      dustPos[i + 1] = (Math.random() - 0.2) * 6;
      dustPos[i + 2] = (Math.random() - 0.5) * 8;
    }
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({
      color: 0x67e8f9,
      size: 0.05,
      transparent: true,
      opacity: 0.45
    });
    const dustPoints = new THREE.Points(dustGeo, dustMat);
    scene.add(dustPoints);

    // Clash Impact Sparks Particles
    const sparkCount = 60;
    const sparkGeo = new THREE.BufferGeometry();
    const sparkPos = new Float32Array(sparkCount * 3);
    const sparkVelo: THREE.Vector3[] = [];
    for (let i = 0; i < sparkCount; i++) {
      sparkPos[i * 3] = 0;
      sparkPos[i * 3 + 1] = 0;
      sparkPos[i * 3 + 2] = 0;
      sparkVelo.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * 6,
          (Math.random() * 4) + 1,
          (Math.random() - 0.5) * 6
        )
      );
    }
    sparkGeo.setAttribute('position', new THREE.BufferAttribute(sparkPos, 3));
    const sparkMat = new THREE.PointsMaterial({
      color: 0xffea00,
      size: 0.12,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending
    });
    const sparkMesh = new THREE.Points(sparkGeo, sparkMat);
    scene.add(sparkMesh);
    impactParticlesRef.current = sparkMesh;

    // --- PROCEDURAL 3D HAND GENERATOR ---
    function buildHand(isPlayer: boolean): HandRig {
      const root = new THREE.Group();
      const armGroup = new THREE.Group();
      const wristGroup = new THREE.Group();
      const palmGroup = new THREE.Group();

      const mainColor = isPlayer ? 0x1e293b : 0x27272a;
      const accentColor = isPlayer ? 0x00e5ff : 0xff7700;
      const skinColor = isPlayer ? 0xd1d5db : 0xe4e4e7;

      // Base PBR Materials
      const palmMat = new THREE.MeshStandardMaterial({
        color: skinColor,
        roughness: 0.38,
        metalness: 0.18
      });

      const armorMat = new THREE.MeshStandardMaterial({
        color: mainColor,
        roughness: 0.25,
        metalness: 0.8
      });

      const neonMat = new THREE.MeshBasicMaterial({
        color: accentColor
      });

      // 1. Forearm & Sleeve
      const armGeo = new THREE.CylinderGeometry(0.38, 0.44, 1.4, 20);
      const armMesh = new THREE.Mesh(armGeo, armorMat);
      armMesh.rotation.z = Math.PI / 2;
      armMesh.position.x = isPlayer ? -1.1 : 1.1;
      armMesh.castShadow = true;
      armMesh.receiveShadow = true;
      armGroup.add(armMesh);

      // Glowing Neon Wrist Band
      const bandGeo = new THREE.TorusGeometry(0.42, 0.04, 16, 32);
      const bandMesh = new THREE.Mesh(bandGeo, neonMat);
      bandMesh.rotation.y = Math.PI / 2;
      bandMesh.position.x = isPlayer ? -0.45 : 0.45;
      armGroup.add(bandMesh);

      // 2. Wrist Joint
      const wristGeo = new THREE.SphereGeometry(0.35, 16, 16);
      const wristMesh = new THREE.Mesh(wristGeo, armorMat);
      wristGroup.add(wristMesh);

      // 3. Palm Mesh
      // Main central palm
      const palmGeo = new THREE.BoxGeometry(0.9, 0.72, 0.32);
      const palmMesh = new THREE.Mesh(palmGeo, palmMat);
      palmMesh.castShadow = true;
      palmMesh.receiveShadow = true;
      palmGroup.add(palmMesh);

      // Cyber Palm Armor Backplate
      const backPlateGeo = new THREE.BoxGeometry(0.78, 0.62, 0.1);
      const backPlate = new THREE.Mesh(backPlateGeo, armorMat);
      backPlate.position.z = -0.16;
      palmGroup.add(backPlate);

      // Small glowing core on the back of hand
      const coreGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.04, 16);
      const coreMesh = new THREE.Mesh(coreGeo, neonMat);
      coreMesh.rotation.x = Math.PI / 2;
      coreMesh.position.z = -0.22;
      palmGroup.add(coreMesh);

      // 4. Finger Builder
      function createFinger(length: number, width: number, isThumb = false): FingerBones {
        const joint1 = new THREE.Group();
        const joint2 = new THREE.Group();
        const joint3 = new THREE.Group();

        const seg1Len = length * 0.42;
        const seg2Len = length * 0.34;
        const seg3Len = length * 0.24;

        // Joint 1 Knuckle
        const k1Geo = new THREE.SphereGeometry(width * 1.05, 12, 12);
        const k1Mesh = new THREE.Mesh(k1Geo, armorMat);
        joint1.add(k1Mesh);

        // Phalanx 1
        const p1Geo = new THREE.CylinderGeometry(width * 0.9, width, seg1Len, 12);
        const p1Mesh = new THREE.Mesh(p1Geo, palmMat);
        p1Mesh.position.y = seg1Len / 2;
        p1Mesh.castShadow = true;
        joint1.add(p1Mesh);

        // Position Joint 2 at end of segment 1
        joint2.position.y = seg1Len;
        joint1.add(joint2);

        // Joint 2 Knuckle
        const k2Geo = new THREE.SphereGeometry(width * 0.95, 12, 12);
        const k2Mesh = new THREE.Mesh(k2Geo, armorMat);
        joint2.add(k2Mesh);

        // Phalanx 2
        const p2Geo = new THREE.CylinderGeometry(width * 0.8, width * 0.9, seg2Len, 12);
        const p2Mesh = new THREE.Mesh(p2Geo, palmMat);
        p2Mesh.position.y = seg2Len / 2;
        p2Mesh.castShadow = true;
        joint2.add(p2Mesh);

        // Position Joint 3 at end of segment 2
        joint3.position.y = seg2Len;
        joint2.add(joint3);

        // Phalanx 3 (Fingertip)
        const p3Geo = new THREE.CylinderGeometry(width * 0.65, width * 0.8, seg3Len, 12);
        const p3Mesh = new THREE.Mesh(p3Geo, palmMat);
        p3Mesh.position.y = seg3Len / 2;
        p3Mesh.castShadow = true;
        joint3.add(p3Mesh);

        // Fingertip cap
        const tipGeo = new THREE.SphereGeometry(width * 0.65, 12, 12);
        const tipMesh = new THREE.Mesh(tipGeo, palmMat);
        tipMesh.position.y = seg3Len;
        joint3.add(tipMesh);

        return { joint1, joint2, joint3 };
      }

      // Attach 5 Fingers
      // Thumb
      const thumb = createFinger(0.65, 0.14, true);
      const thumbOffset = isPlayer ? 0.42 : -0.42;
      thumb.joint1.position.set(thumbOffset, -0.15, 0.08);
      thumb.joint1.rotation.z = isPlayer ? -Math.PI / 4 : Math.PI / 4;
      thumb.joint1.rotation.y = isPlayer ? 0.4 : -0.4;
      palmGroup.add(thumb.joint1);

      // Index
      const index = createFinger(0.78, 0.125);
      index.joint1.position.set(isPlayer ? 0.3 : -0.3, 0.36, 0);
      palmGroup.add(index.joint1);

      // Middle
      const middle = createFinger(0.86, 0.13);
      middle.joint1.position.set(isPlayer ? 0.1 : -0.1, 0.38, 0);
      palmGroup.add(middle.joint1);

      // Ring
      const ring = createFinger(0.76, 0.125);
      ring.joint1.position.set(isPlayer ? -0.12 : 0.12, 0.36, 0);
      palmGroup.add(ring.joint1);

      // Pinky
      const pinky = createFinger(0.62, 0.11);
      pinky.joint1.position.set(isPlayer ? -0.32 : 0.32, 0.32, 0);
      palmGroup.add(pinky.joint1);

      // Assemble hierarchy
      wristGroup.add(palmGroup);
      armGroup.add(wristGroup);
      root.add(armGroup);
      scene.add(root);

      const baseX = isPlayer ? -2.2 : 2.2;
      root.position.set(baseX, 0, 0);

      // Orientation so hands face each other
      if (isPlayer) {
        root.rotation.set(0.1, 0.75, -0.1);
      } else {
        root.rotation.set(0.1, -0.75, 0.1);
      }

      return {
        root,
        armGroup,
        wristGroup,
        palmGroup,
        thumb,
        index,
        middle,
        ring,
        pinky,
        isPlayer,
        baseX,
        targetPos: new THREE.Vector3(baseX, 0, 0),
        targetRot: root.rotation.clone(),
        currentGesture: 'idle'
      };
    }

    const playerRig = buildHand(true);
    const opponentRig = buildHand(false);
    rigPlayerRef.current = playerRig;
    rigOpponentRef.current = opponentRig;

    // --- RESIZE LISTENER ---
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      updateCameraPos();
    };
    window.addEventListener('resize', handleResize);

    // --- ANIMATION RENDER LOOP ---
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();
      const delta = Math.min(clock.getDelta(), 0.1);

      // Arena ring slow rotation
      ringGroup.rotation.y = elapsedTime * 0.15;
      dustPoints.rotation.y = elapsedTime * 0.05;

      // Update clash particles if active
      if (sparkMat.opacity > 0) {
        const positions = sparkGeo.attributes.position.array as Float32Array;
        for (let i = 0; i < sparkCount; i++) {
          positions[i * 3] += sparkVelo[i].x * delta;
          positions[i * 3 + 1] += sparkVelo[i].y * delta;
          positions[i * 3 + 2] += sparkVelo[i].z * delta;
          sparkVelo[i].y -= 9.8 * delta; // gravity
        }
        sparkGeo.attributes.position.needsUpdate = true;
        sparkMat.opacity = Math.max(0, sparkMat.opacity - delta * 1.8);
      }

      // Camera Shake
      if (cameraShakeRef.current > 0) {
        const shake = cameraShakeRef.current;
        camera.position.x += (Math.random() - 0.5) * shake;
        camera.position.y += (Math.random() - 0.5) * shake;
        cameraShakeRef.current = Math.max(0, cameraShakeRef.current - delta * 4);
      } else {
        // Return camera smoothly to base
        const curAspect = (container.clientWidth || window.innerWidth) / (container.clientHeight || 450);
        const targetCamY = curAspect < 1.0 ? 1.4 : 0.9;
        const targetCamZ = curAspect < 1.0 ? 8.2 : 6.2;
        camera.position.y = THREE.MathUtils.lerp(camera.position.y, targetCamY, 0.1);
        camera.position.x = THREE.MathUtils.lerp(camera.position.x, 0, 0.1);
        camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetCamZ, 0.1);
      }

      // Smooth Rig Movement
      [playerRig, opponentRig].forEach((rig) => {
        // Smooth position & rotation lerping
        rig.root.position.lerp(rig.targetPos, 0.12);
        rig.root.quaternion.slerp(new THREE.Quaternion().setFromEuler(rig.targetRot), 0.12);

        // Idle floating hovering wave
        if (rig.currentGesture === 'idle') {
          const offset = rig.isPlayer ? 0 : Math.PI;
          const bobY = Math.sin(elapsedTime * 2.2 + offset) * 0.08;
          rig.root.position.y = rig.targetPos.y + bobY;
          rig.wristGroup.rotation.z = Math.sin(elapsedTime * 1.8 + offset) * 0.05;
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (container && renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  // --- GESTURE APPLICATION HELPER ---
  const applyGesture = (
    rig: HandRig,
    gesture: HandChoice | 'idle' | 'countdown',
    speed: number = 0.2
  ) => {
    rig.currentGesture = gesture;

    const setJoints = (finger: FingerBones, r1: number, r2: number, r3: number, spreadZ: number = 0) => {
      finger.joint1.rotation.x = THREE.MathUtils.lerp(finger.joint1.rotation.x, r1, speed);
      finger.joint2.rotation.x = THREE.MathUtils.lerp(finger.joint2.rotation.x, r2, speed);
      finger.joint3.rotation.x = THREE.MathUtils.lerp(finger.joint3.rotation.x, r3, speed);
      finger.joint1.rotation.z = THREE.MathUtils.lerp(finger.joint1.rotation.z, spreadZ, speed);
    };

    if (gesture === 'idle') {
      // Natural, relaxed hand curvature
      setJoints(rig.index, 0.28, 0.35, 0.2, rig.isPlayer ? -0.05 : 0.05);
      setJoints(rig.middle, 0.32, 0.38, 0.25, 0);
      setJoints(rig.ring, 0.38, 0.42, 0.28, rig.isPlayer ? 0.05 : -0.05);
      setJoints(rig.pinky, 0.42, 0.45, 0.3, rig.isPlayer ? 0.1 : -0.1);
      // Thumb resting
      rig.thumb.joint1.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint1.rotation.x, 0.3, speed);
      rig.thumb.joint2.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint2.rotation.x, 0.2, speed);
      rig.thumb.joint3.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint3.rotation.x, 0.2, speed);
    } else if (gesture === 'countdown') {
      // Tense ready fist during 3-2-1
      setJoints(rig.index, 1.4, 1.6, 1.2, 0);
      setJoints(rig.middle, 1.45, 1.65, 1.2, 0);
      setJoints(rig.ring, 1.5, 1.7, 1.2, 0);
      setJoints(rig.pinky, 1.5, 1.7, 1.2, 0);
      rig.thumb.joint1.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint1.rotation.x, 1.2, speed);
      rig.thumb.joint2.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint2.rotation.x, 1.4, speed);
      rig.thumb.joint3.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint3.rotation.x, 1.0, speed);
    } else if (gesture === 'rock') {
      // ROCK: Tight, solid fist with thumb firmly wrapped across fingers
      setJoints(rig.index, 1.55, 1.75, 1.35, 0);
      setJoints(rig.middle, 1.6, 1.8, 1.4, 0);
      setJoints(rig.ring, 1.62, 1.82, 1.4, 0);
      setJoints(rig.pinky, 1.65, 1.85, 1.4, 0);
      // Thumb locked over knuckles
      rig.thumb.joint1.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint1.rotation.x, 1.3, speed);
      rig.thumb.joint2.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint2.rotation.x, 1.6, speed);
      rig.thumb.joint3.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint3.rotation.x, 1.2, speed);
    } else if (gesture === 'paper') {
      // PAPER: All fingers completely extended straight out with slight fan spread
      const dir = rig.isPlayer ? 1 : -1;
      setJoints(rig.index, -0.05, 0, 0, -0.18 * dir);
      setJoints(rig.middle, -0.05, 0, 0, -0.04 * dir);
      setJoints(rig.ring, -0.05, 0, 0, 0.12 * dir);
      setJoints(rig.pinky, -0.05, 0, 0, 0.28 * dir);
      // Thumb extended wide
      rig.thumb.joint1.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint1.rotation.x, -0.2, speed);
      rig.thumb.joint2.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint2.rotation.x, -0.1, speed);
      rig.thumb.joint3.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint3.rotation.x, 0, speed);
    } else if (gesture === 'scissors') {
      // SCISSORS: Index and Middle fingers extended in a sharp V shape! Ring, Pinky & Thumb curled in.
      const dir = rig.isPlayer ? 1 : -1;
      // Index & Middle spread in V
      setJoints(rig.index, -0.05, 0, 0, -0.25 * dir);
      setJoints(rig.middle, -0.05, 0, 0, 0.22 * dir);
      // Ring & Pinky curled tightly inside
      setJoints(rig.ring, 1.65, 1.8, 1.4, 0);
      setJoints(rig.pinky, 1.7, 1.85, 1.4, 0);
      // Thumb folded over ring finger
      rig.thumb.joint1.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint1.rotation.x, 1.3, speed);
      rig.thumb.joint2.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint2.rotation.x, 1.4, speed);
      rig.thumb.joint3.rotation.x = THREE.MathUtils.lerp(rig.thumb.joint3.rotation.x, 1.0, speed);
    }
  };

  // --- REACT TO GAME PHASE CHANGES ---
  useEffect(() => {
    const pRig = rigPlayerRef.current;
    const opRig = rigOpponentRef.current;
    if (!pRig || !opRig) return;

    if (phase === 'ready') {
      // Both hands idle in starting positions
      pRig.targetPos.set(pRig.baseX, 0, 0);
      pRig.targetRot.set(0.1, 0.75, -0.1);
      opRig.targetPos.set(opRig.baseX, 0, 0);
      opRig.targetRot.set(0.1, -0.75, 0.1);

      applyGesture(pRig, 'idle', 0.25);
      applyGesture(opRig, 'idle', 0.25);
    } else if (phase === 'countdown') {
      // Hands pump up and down in unison on countdown steps (3, 2, 1)
      const pumpY = countdownStep % 2 === 1 ? 0.45 : -0.2;
      pRig.targetPos.set(pRig.baseX + 0.35, pumpY, 0.2);
      opRig.targetPos.set(opRig.baseX - 0.35, pumpY, 0.2);

      pRig.targetRot.set(-0.2, 0.6, -0.2);
      opRig.targetRot.set(-0.2, -0.6, 0.2);

      applyGesture(pRig, 'countdown', 0.3);
      applyGesture(opRig, 'countdown', 0.3);
    } else if (phase === 'reveal') {
      // POWER CLASH: Both hands thrust rapidly toward center arena!
      pRig.targetPos.set(-0.85, 0, 0.5);
      pRig.targetRot.set(0.05, 0.45, 0);

      opRig.targetPos.set(0.85, 0, 0.5);
      opRig.targetRot.set(0.05, -0.45, 0);

      if (playerChoice) applyGesture(pRig, playerChoice, 0.4);
      if (opponentChoice) applyGesture(opRig, opponentChoice, 0.4);

      // Trigger spark particles & camera shake
      if (impactParticlesRef.current) {
        const mat = impactParticlesRef.current.material as THREE.PointsMaterial;
        mat.opacity = 1.0;
        cameraShakeRef.current = 0.08;
      }
    } else if (phase === 'roundResult' || phase === 'matchResult') {
      // Keep selected gestures
      if (playerChoice) applyGesture(pRig, playerChoice, 0.2);
      if (opponentChoice) applyGesture(opRig, opponentChoice, 0.2);

      if (roundOutcome === 'win') {
        // Player victory pump!
        pRig.targetPos.set(-1.0, 0.4, 0.3);
        pRig.targetRot.set(-0.25, 0.5, -0.15);
        // Opponent staggered back
        opRig.targetPos.set(opRig.baseX + 0.3, -0.35, -0.4);
        opRig.targetRot.set(0.4, -0.8, 0.3);
      } else if (roundOutcome === 'lose') {
        // Player staggered back
        pRig.targetPos.set(pRig.baseX - 0.3, -0.35, -0.4);
        pRig.targetRot.set(0.4, 0.8, -0.3);
        // Opponent victory pump!
        opRig.targetPos.set(1.0, 0.4, 0.3);
        opRig.targetRot.set(-0.25, -0.5, 0.15);
      } else {
        // Draw: slight bounce recoil
        pRig.targetPos.set(-1.4, 0, 0);
        opRig.targetPos.set(1.4, 0, 0);
      }
    }
  }, [phase, countdownStep, playerChoice, opponentChoice, roundOutcome]);

  return (
    <div className="relative w-full h-[340px] sm:h-[420px] md:h-[480px] overflow-hidden select-none">
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="absolute inset-0 w-full h-full" />

      {/* Floating Arena Atmosphere Labels */}
      <div className="absolute top-3 left-4 flex items-center gap-2 pointer-events-none">
        <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00e5ff]" />
        <span className="text-xs uppercase font-bold tracking-widest text-cyan-300 drop-shadow">
          YOU (PLAYER)
        </span>
      </div>

      <div className="absolute top-3 right-4 flex items-center gap-2 pointer-events-none">
        <span className="text-xs uppercase font-bold tracking-widest text-amber-400 drop-shadow">
          OPPONENT (NEXUS AI)
        </span>
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse shadow-[0_0_8px_#ff9100]" />
      </div>

      {/* Big Animated Center Countdown Pulse */}
      {phase === 'countdown' && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          <div
            key={countdownStep}
            className="text-7xl sm:text-8xl md:text-9xl font-black italic text-transparent bg-clip-text bg-gradient-to-b from-yellow-300 via-amber-400 to-red-500 drop-shadow-[0_0_25px_rgba(250,204,21,0.8)] animate-[ping_0.5s_cubic-bezier(0,0,0.2,1)]"
          >
            {countdownStep}
          </div>
        </div>
      )}

      {/* Choice reveal labels over each hand during reveal/result */}
      {(phase === 'reveal' || phase === 'roundResult' || phase === 'matchResult') && (
        <>
          {playerChoice && (
            <div className="absolute bottom-6 left-6 sm:left-12 flex flex-col items-start pointer-events-none animate-fade-in">
              <span className="text-[10px] tracking-wider uppercase text-cyan-300/80 font-semibold">
                YOUR WEAPON
              </span>
              <span className="text-xl sm:text-2xl font-black tracking-wider text-cyan-300 drop-shadow-[0_0_12px_#00e5ff]">
                {playerChoice.toUpperCase()}
              </span>
            </div>
          )}

          {opponentChoice && (
            <div className="absolute bottom-6 right-6 sm:right-12 flex flex-col items-end pointer-events-none animate-fade-in">
              <span className="text-[10px] tracking-wider uppercase text-amber-300/80 font-semibold">
                NEXUS WEAPON
              </span>
              <span className="text-xl sm:text-2xl font-black tracking-wider text-amber-400 drop-shadow-[0_0_12px_#ff9100]">
                {opponentChoice.toUpperCase()}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
};
