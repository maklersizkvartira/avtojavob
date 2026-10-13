import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  HandChoice,
  GamePhase,
  RoundOutcome,
  AIDifficulty,
  GameMode,
  MatchState
} from './types';
import {
  determineRoundWinner,
  getAIMove,
  createInitialMatchState
} from './utils/gameLogic';
import { sound } from './utils/audio';
import { HandArena3D } from './components/HandArena3D';
import { ScoreBoard } from './components/ScoreBoard';
import { ChoiceButtons } from './components/ChoiceButtons';
import { TopBar } from './components/TopBar';
import { ResultBanner } from './components/ResultBanner';
import { MatchWinnerModal } from './components/MatchWinnerModal';
import { StatsModal } from './components/StatsModal';
import { OnlineLobbyModal } from './components/OnlineLobbyModal';
import { io, Socket } from 'socket.io-client';

export const App: React.FC = () => {
  // Game State
  const [phase, setPhase] = useState<GamePhase>('ready');
  const [countdownStep, setCountdownStep] = useState<number>(3);
  const [playerChoice, setPlayerChoice] = useState<HandChoice | null>(null);
  const [opponentChoice, setOpponentChoice] = useState<HandChoice | null>(null);
  const [roundOutcome, setRoundOutcome] = useState<RoundOutcome | null>(null);
  const [matchState, setMatchState] = useState<MatchState>(createInitialMatchState());
  const [difficulty, setDifficulty] = useState<AIDifficulty>('tactical');
  const [isMuted, setIsMuted] = useState<boolean>(sound.isMuted());

  // UI Modals
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [showOnlineLobby, setShowOnlineLobby] = useState(false);

  // Online Multiplayer State
  const [gameMode, setGameMode] = useState<GameMode>('ai');
  const [roomCode, setRoomCode] = useState<string | null>(null);
  const [onlineCount, setOnlineCount] = useState<number>(1);
  const [onlineRole, setOnlineRole] = useState<'p1' | 'p2' | null>(null);
  const socketRef = useRef<Socket | null>(null);

  // Sound Toggle Handler
  const handleToggleSound = () => {
    const muted = sound.toggleMute();
    setIsMuted(muted);
  };

  // Connect to backend Socket.IO for multiplayer & live stats
  useEffect(() => {
    const socket = io(window.location.origin, {
      transports: ['websocket', 'polling']
    });
    socketRef.current = socket;

    socket.on('online_count', (count: number) => {
      setOnlineCount(count);
    });

    socket.on('room_created', ({ code, role }: { code: string; role: 'p1' }) => {
      setRoomCode(code);
      setOnlineRole(role);
      setGameMode('online');
    });

    socket.on('match_ready', () => {
      setShowOnlineLobby(false);
      resetMatch();
      setGameMode('online');
    });

    socket.on('round_revealed', (data: {
      p1Choice: HandChoice;
      p2Choice: HandChoice;
      roundWinner: 'p1' | 'p2' | 'draw';
      p1Score: number;
      p2Score: number;
      matchWinner: 'p1' | 'p2' | null;
    }) => {
      const isP1 = onlineRole === 'p1';
      const myChoice = isP1 ? data.p1Choice : data.p2Choice;
      const opChoice = isP1 ? data.p2Choice : data.p1Choice;

      setPlayerChoice(myChoice);
      setOpponentChoice(opChoice);

      let outcome: RoundOutcome = 'draw';
      if (data.roundWinner === 'p1') outcome = isP1 ? 'win' : 'lose';
      else if (data.roundWinner === 'p2') outcome = isP1 ? 'lose' : 'win';

      setRoundOutcome(outcome);
      setPhase('reveal');
      sound.playImpact();

      setTimeout(() => {
        if (outcome === 'win') sound.playWin();
        else if (outcome === 'lose') sound.playLose();
        else sound.playDraw();

        const pScore = isP1 ? data.p1Score : data.p2Score;
        const opScore = isP1 ? data.p2Score : data.p1Score;

        setMatchState(prev => ({
          ...prev,
          playerScore: pScore,
          opponentScore: opScore,
          roundsPlayed: prev.roundsPlayed + 1,
          decisiveRounds: pScore + opScore,
          winner: data.matchWinner ? (data.matchWinner === onlineRole ? 'player' : 'opponent') : null
        }));

        if (data.matchWinner) {
          setPhase('matchResult');
        } else {
          setPhase('roundResult');
        }
      }, 1100);
    });

    return () => {
      socket.disconnect();
    };
  }, [onlineRole]);

  // Restart match handler
  const resetMatch = useCallback(() => {
    setMatchState(createInitialMatchState());
    setPlayerChoice(null);
    setOpponentChoice(null);
    setRoundOutcome(null);
    setPhase('ready');
    setCountdownStep(3);
    sound.playTap();
  }, []);

  // Post match results to backend API
  const recordMatchResults = useCallback((winner: 'player' | 'opponent', finalState: MatchState) => {
    fetch('/api/stats/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        winner,
        roundsPlayed: finalState.roundsPlayed,
        choices: finalState.history.map(h => h.playerChoice)
      })
    }).catch(() => {
      // Offline fallback
    });
  }, []);

  // Handle Player Selecting Rock, Paper, or Scissors
  const handleSelectChoice = useCallback((choice: HandChoice) => {
    if (phase !== 'ready') return;

    sound.playTap();
    setPlayerChoice(choice);

    if (gameMode === 'online' && roomCode && socketRef.current) {
      // In online mode, submit choice to server
      socketRef.current.emit('submit_choice', { code: roomCode, choice });
      setPhase('countdown');
      setCountdownStep(3);
      sound.playCountdownTick(3);
      return;
    }

    // --- SOLO VS AI FLOW ---
    // Opponent picks independently
    const playerMoveHistory = matchState.history.map(h => h.playerChoice);
    const botChoice = getAIMove(difficulty, playerMoveHistory);
    setOpponentChoice(botChoice);

    // Enter Phase B: Countdown 3, 2, 1
    setPhase('countdown');
    setCountdownStep(3);
    sound.playCountdownTick(3);

    const step2Timer = setTimeout(() => {
      setCountdownStep(2);
      sound.playCountdownTick(2);
    }, 600);

    const step1Timer = setTimeout(() => {
      setCountdownStep(1);
      sound.playCountdownTick(1);
    }, 1200);

    const revealTimer = setTimeout(() => {
      // Enter Phase C: Reveal
      setPhase('reveal');
      sound.playImpact();

      const outcome = determineRoundWinner(choice, botChoice);
      setRoundOutcome(outcome);

      // Play outcome audio
      setTimeout(() => {
        if (outcome === 'win') sound.playWin();
        else if (outcome === 'lose') sound.playLose();
        else sound.playDraw();
      }, 350);

      // Enter Phase D: Score Resolution
      setTimeout(() => {
        setMatchState(prev => {
          let newPScore = prev.playerScore;
          let newOpScore = prev.opponentScore;
          const isDecisive = outcome !== 'draw';

          if (outcome === 'win') newPScore += 1;
          else if (outcome === 'lose') newOpScore += 1;

          const newDecisive = newPScore + newOpScore;
          const newHistory = [
            ...prev.history,
            {
              roundNumber: prev.roundsPlayed + 1,
              playerChoice: choice,
              opponentChoice: botChoice,
              outcome,
              isDecisive
            }
          ];

          let matchWinner: 'player' | 'opponent' | null = null;
          if (newPScore >= 2) matchWinner = 'player';
          else if (newOpScore >= 2) matchWinner = 'opponent';

          const updated: MatchState = {
            playerScore: newPScore,
            opponentScore: newOpScore,
            roundsPlayed: prev.roundsPlayed + 1,
            decisiveRounds: newDecisive,
            history: newHistory,
            winner: matchWinner
          };

          if (matchWinner) {
            setPhase('matchResult');
            recordMatchResults(matchWinner, updated);
          } else {
            setPhase('roundResult');
          }

          return updated;
        });
      }, 1200);
    }, 1800);

    return () => {
      clearTimeout(step2Timer);
      clearTimeout(step1Timer);
      clearTimeout(revealTimer);
    };
  }, [phase, gameMode, roomCode, matchState.history, difficulty, recordMatchResults]);

  // Proceed to Next Round
  const handleNextRound = useCallback(() => {
    if (matchState.winner) return;
    sound.playTap();
    setPlayerChoice(null);
    setOpponentChoice(null);
    setRoundOutcome(null);
    setPhase('ready');
    setCountdownStep(3);
  }, [matchState.winner]);

  // Keyboard Shortcuts (1=Rock, 2=Paper, 3=Scissors, Space/Enter=Next)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (phase === 'ready') {
        if (e.key === '1' || e.key.toLowerCase() === 'r') handleSelectChoice('rock');
        else if (e.key === '2' || e.key.toLowerCase() === 'p') handleSelectChoice('paper');
        else if (e.key === '3' || e.key.toLowerCase() === 's') handleSelectChoice('scissors');
      } else if (phase === 'roundResult') {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleNextRound();
        }
      } else if (phase === 'matchResult') {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          resetMatch();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [phase, handleSelectChoice, handleNextRound, resetMatch]);

  // Online Multiplayer handlers
  const handleCreateRoom = (name: string) => {
    if (socketRef.current) {
      socketRef.current.emit('create_room', { playerName: name });
    }
  };

  const handleJoinRoom = (code: string, name: string) => {
    if (socketRef.current) {
      setOnlineRole('p2');
      setRoomCode(code);
      socketRef.current.emit('join_room', { code, playerName: name });
    }
  };

  const matchInProgress = matchState.playerScore > 0 || matchState.opponentScore > 0 || matchState.history.length > 0;

  return (
    <div className="relative min-h-screen w-full bg-[#080918] text-slate-100 flex flex-col justify-between overflow-x-hidden font-['Outfit',sans-serif]">
      {/* Dynamic Background Arena Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(99,102,241,0.15),transparent_70%)] pointer-events-none" />
      <div className="absolute top-0 left-0 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-0 right-0 w-72 h-72 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Bar Header */}
      <TopBar
        isMuted={isMuted}
        onToggleSound={handleToggleSound}
        onResetMatch={resetMatch}
        difficulty={difficulty}
        onChangeDifficulty={setDifficulty}
        gameMode={gameMode}
        onOpenOnlineLobby={() => setShowOnlineLobby(true)}
        onOpenStats={() => setShowStatsModal(true)}
        matchInProgress={matchInProgress}
      />

      {/* Main Game Screen Content */}
      <main className="flex-1 flex flex-col justify-center items-center w-full max-w-4xl mx-auto px-2 relative z-10">
        {/* Score Board with Best of 3 slots */}
        <ScoreBoard
          matchState={matchState}
          lastOutcome={roundOutcome}
        />

        {/* 3D Hand Arena Viewport */}
        <div className="w-full my-1 sm:my-2">
          <HandArena3D
            playerChoice={playerChoice}
            opponentChoice={opponentChoice}
            phase={phase}
            countdownStep={countdownStep}
            roundOutcome={roundOutcome}
          />
        </div>

        {/* Round Outcome Banner (between rounds) */}
        {phase === 'roundResult' && (
          <ResultBanner
            outcome={roundOutcome}
            playerChoice={playerChoice}
            opponentChoice={opponentChoice}
            onNextRound={handleNextRound}
            isMatchOver={Boolean(matchState.winner)}
          />
        )}

        {/* Choice Buttons (Ready phase) */}
        <ChoiceButtons
          onSelectChoice={handleSelectChoice}
          selectedChoice={playerChoice}
          phase={phase}
        />
      </main>

      {/* Mobile-Friendly Bottom Footer */}
      <footer className="w-full text-center py-2 text-[11px] text-slate-500 font-medium select-none">
        <span>HANDS OF GLORY • Best of 3 Arena • First to 2 Wins</span>
      </footer>

      {/* Match Decisive Winner Modal */}
      {phase === 'matchResult' && (
        <MatchWinnerModal
          winner={matchState.winner}
          matchState={matchState}
          onPlayAgain={resetMatch}
        />
      )}

      {/* Arena Statistics & Rankings Modal */}
      <StatsModal
        isOpen={showStatsModal}
        onClose={() => setShowStatsModal(false)}
      />

      {/* Live Online 1v1 Room Modal */}
      <OnlineLobbyModal
        isOpen={showOnlineLobby}
        onClose={() => setShowOnlineLobby(false)}
        onCreateRoom={handleCreateRoom}
        onJoinRoom={handleJoinRoom}
        roomCode={roomCode}
        onlineCount={onlineCount}
      />
    </div>
  );
};
export default App;
