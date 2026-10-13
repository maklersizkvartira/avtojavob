import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

app.use(cors());
app.use(express.json());

// In-memory persistent data store
const DATA_DIR = path.join(__dirname, 'data');
if (!fs.existsSync(DATA_DIR)) {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  } catch (e) {
    console.error('Failed to create data dir:', e);
  }
}

const STATS_FILE = path.join(DATA_DIR, 'stats.json');
let stats = {
  totalMatches: 42,
  playerWins: 24,
  botWins: 18,
  draws: 7,
  choices: {
    rock: 68,
    paper: 54,
    scissors: 61
  },
  winStreakRecord: 5,
  recentMatches: []
};

// Load stats from disk if available
if (fs.existsSync(STATS_FILE)) {
  try {
    const raw = fs.readFileSync(STATS_FILE, 'utf-8');
    stats = { ...stats, ...JSON.parse(raw) };
  } catch (err) {
    console.warn('Could not read existing stats.json, using defaults.');
  }
}

function saveStats() {
  try {
    fs.writeFileSync(STATS_FILE, JSON.stringify(stats, null, 2));
  } catch (e) {
    console.warn('Could not write stats to disk:', e.message);
  }
}

let leaderboard = [
  { name: 'Ahmad_King', streak: 7, date: '2026-10-12' },
  { name: 'CyberTitan', streak: 6, date: '2026-10-12' },
  { name: 'NeonSamurai', streak: 5, date: '2026-10-13' },
  { name: 'ShadowFist', streak: 4, date: '2026-10-13' },
  { name: 'QuantumMaster', streak: 3, date: '2026-10-13' }
];

// REST API Endpoints
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    game: 'Hands of Glory',
    uptime: Math.floor(process.uptime()),
    timestamp: new Date().toISOString()
  });
});

app.get('/api/stats', (req, res) => {
  res.json(stats);
});

app.post('/api/stats/record', (req, res) => {
  const { winner, roundsPlayed, choices } = req.body;
  stats.totalMatches += 1;
  if (winner === 'player') stats.playerWins += 1;
  else if (winner === 'opponent' || winner === 'bot') stats.botWins += 1;
  else if (winner === 'draw') stats.draws += 1;

  if (Array.isArray(choices)) {
    choices.forEach(ch => {
      const lower = String(ch).toLowerCase();
      if (stats.choices[lower] !== undefined) {
        stats.choices[lower] += 1;
      }
    });
  }

  stats.recentMatches.unshift({
    id: Date.now(),
    winner,
    roundsPlayed: roundsPlayed || 2,
    timestamp: new Date().toISOString()
  });
  if (stats.recentMatches.length > 20) {
    stats.recentMatches = stats.recentMatches.slice(0, 20);
  }

  saveStats();
  res.json({ success: true, stats });
});

app.get('/api/leaderboard', (req, res) => {
  res.json(leaderboard);
});

app.post('/api/leaderboard', (req, res) => {
  const { name, streak } = req.body;
  if (name && typeof streak === 'number') {
    leaderboard.push({
      name: String(name).slice(0, 20),
      streak,
      date: new Date().toISOString().split('T')[0]
    });
    leaderboard.sort((a, b) => b.streak - a.streak);
    leaderboard = leaderboard.slice(0, 10);
    if (streak > stats.winStreakRecord) {
      stats.winStreakRecord = streak;
      saveStats();
    }
  }
  res.json({ success: true, leaderboard });
});

// Serve static frontend assets from 'dist'
const distPath = path.join(__dirname, 'dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
  });
} else {
  app.get('/', (req, res) => {
    res.send('<h1>Hands of Glory Backend Running</h1><p>Frontend build pending. Run <code>npm run build</code> or connect via Vite dev server.</p>');
  });
}

// Realtime Multiplayer Rooms via Socket.io
const rooms = new Map();

function determineWinner(c1, c2) {
  if (c1 === c2) return 'draw';
  if (
    (c1 === 'rock' && c2 === 'scissors') ||
    (c1 === 'paper' && c2 === 'rock') ||
    (c1 === 'scissors' && c2 === 'paper')
  ) {
    return 'p1';
  }
  return 'p2';
}

io.on('connection', (socket) => {
  io.emit('online_count', io.engine.clientsCount);

  socket.on('create_room', ({ playerName }) => {
    const code = Math.random().toString(36).substring(2, 6).toUpperCase();
    const room = {
      code,
      players: {
        [socket.id]: {
          id: socket.id,
          name: playerName || 'Player 1',
          score: 0,
          choice: null,
          ready: true
        }
      },
      playerList: [socket.id],
      roundsDecided: 0,
      currentRound: 1,
      matchWinner: null
    };

    rooms.set(code, room);
    socket.join(code);
    socket.emit('room_created', { code, role: 'p1' });
  });

  socket.on('join_room', ({ code, playerName }) => {
    const cleanCode = String(code).trim().toUpperCase();
    const room = rooms.get(cleanCode);

    if (!room) {
      return socket.emit('join_error', { message: 'Room not found. Check the code!' });
    }
    if (room.playerList.length >= 2) {
      return socket.emit('join_error', { message: 'Room is already full!' });
    }

    room.players[socket.id] = {
      id: socket.id,
      name: playerName || 'Player 2',
      score: 0,
      choice: null,
      ready: true
    };
    room.playerList.push(socket.id);
    socket.join(cleanCode);

    const p1Id = room.playerList[0];
    const p2Id = room.playerList[1];

    io.to(cleanCode).emit('match_ready', {
      code: cleanCode,
      p1: { id: p1Id, name: room.players[p1Id].name, score: 0 },
      p2: { id: p2Id, name: room.players[p2Id].name, score: 0 }
    });
  });

  socket.on('submit_choice', ({ code, choice }) => {
    const cleanCode = String(code).trim().toUpperCase();
    const room = rooms.get(cleanCode);
    if (!room || room.matchWinner) return;

    const player = room.players[socket.id];
    if (!player) return;

    player.choice = choice;

    // Check if both players picked
    const p1Id = room.playerList[0];
    const p2Id = room.playerList[1];

    if (p1Id && p2Id && room.players[p1Id].choice && room.players[p2Id].choice) {
      const c1 = room.players[p1Id].choice;
      const c2 = room.players[p2Id].choice;
      const result = determineWinner(c1, c2);

      if (result === 'p1') {
        room.players[p1Id].score += 1;
        room.roundsDecided += 1;
      } else if (result === 'p2') {
        room.players[p2Id].score += 1;
        room.roundsDecided += 1;
      }

      let matchWinner = null;
      if (room.players[p1Id].score >= 2) {
        matchWinner = 'p1';
        room.matchWinner = 'p1';
      } else if (room.players[p2Id].score >= 2) {
        matchWinner = 'p2';
        room.matchWinner = 'p2';
      }

      io.to(cleanCode).emit('round_revealed', {
        p1Choice: c1,
        p2Choice: c2,
        roundWinner: result,
        p1Score: room.players[p1Id].score,
        p2Score: room.players[p2Id].score,
        roundsDecided: room.roundsDecided,
        matchWinner
      });

      // Reset choices for next round
      room.players[p1Id].choice = null;
      room.players[p2Id].choice = null;
      if (!matchWinner) {
        room.currentRound += 1;
      }
    } else {
      socket.to(cleanCode).emit('opponent_locked');
    }
  });

  socket.on('restart_room', ({ code }) => {
    const cleanCode = String(code).trim().toUpperCase();
    const room = rooms.get(cleanCode);
    if (!room) return;

    room.roundsDecided = 0;
    room.currentRound = 1;
    room.matchWinner = null;
    room.playerList.forEach(pid => {
      if (room.players[pid]) {
        room.players[pid].score = 0;
        room.players[pid].choice = null;
      }
    });

    io.to(cleanCode).emit('room_restarted', {
      p1Score: 0,
      p2Score: 0
    });
  });

  socket.on('disconnect', () => {
    io.emit('online_count', io.engine.clientsCount);
    for (const [code, room] of rooms.entries()) {
      if (room.playerList.includes(socket.id)) {
        socket.to(code).emit('opponent_left');
        rooms.delete(code);
      }
    }
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`⚡ Hands of Glory Game Server listening on port ${PORT}`);
});
