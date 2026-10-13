# ⚡ HANDS OF GLORY — 3D Cyber Arena

An elite, mobile-first 3D Rock Paper Scissors arena game featuring articulated anatomical 3D hands, synchronized countdown animations, Web Audio synthesizer effects, a best-of-three decisive round match system, and a live real-time backend ready for Railway deployment.

![Hands of Glory](https://img.shields.io/badge/Status-Live%20Arena-00e5ff?style=for-the-badge)
![Platform](https://img.shields.io/badge/Deploy-Railway-6851ff?style=for-the-badge)
![Tech](https://img.shields.io/badge/Three.js-WebGL-f59e0b?style=for-the-badge)

---

## 🎮 Core Game Features

### 1. Realistic Articulated 3D Hands (Three.js)
- **Procedural Anatomical Modeling**: Full hand skeleton with wrist cuff, palm core, and 5 fully articulated fingers (Thumb, Index, Middle, Ring, Pinky).
- **Recognizable Gestures**:
  - ✊ **ROCK**: Solid clenched fist with thumb locked over knuckles.
  - ✋ **PAPER**: Wide fanned-out open hand with extended fingers.
  - ✌️ **SCISSORS**: Sharp V-shape extended index & middle fingers, tightly curled ring and pinky.
- **Dynamic Physics & Lighting**: PBR metallic-cyber materials, dual rim lights (Electric Cyan for Player, Amber Flame for Opponent), holographic arena rings, and impact sparks on clash.

### 2. Best of Three Match Rules
- Match consists of up to **3 decisive rounds**.
- **First to win 2 rounds wins the match immediately** (can end 2-0 or 2-1).
- **Draws do not award points**: Both players replay the round slot without wasting a decisive match point.

### 3. Tactile Sound Engine (Web Audio API)
- Pure synthesized Web Audio (zero audio asset latency and no 404s).
- Crisp button taps, 3-2-1 countdown ticks, heavy sub-bass clash impacts, victory fanfares, and defeat tones.
- Mute/Unmute state persisted in `localStorage`.

### 4. Real-time Backend & Online 1v1 Multiplayer
- Built with **Node.js, Express, and Socket.IO**.
- **Solo vs AI**: Choose between *Novice* (pure random), *Tactical* (counter-play psychology), and *Grandmaster* (frequency matrix analysis).
- **Online 1v1 Room**: Create a private 4-letter room code (e.g., `GLOR`), invite a friend, and play live in real-time.
- **Live Leaderboard & Statistics**: Persistent stats tracking total matches, weapon pick frequency, and win streak records.

---

## 🚀 Running Locally

```bash
# Install dependencies
npm install

# Run unit test suite (validates all RPS matchups and Best-of-3 rules)
npx tsx tests/gameLogic.test.js

# Build production bundle
npm run build

# Start fullstack server (Express + Socket.IO on port 3001)
npm start
```

Open [http://localhost:3001](http://localhost:3001) in your browser.

---

## 🚂 Railway Deployment

This project is fully pre-configured for **Railway** deployment:

1. **`railway.json`**:
   Configured with Nixpacks to automatically execute `npm install && npm run build` and start via `node server.js`.
2. **`Procfile`**:
   Contains `web: node server.js`.
3. **`Dockerfile`**:
   Provided as an alternate containerized build option.
4. **Environment Variables**:
   - `PORT`: Automatically assigned by Railway.
   - `NODE_ENV`: `production`.
