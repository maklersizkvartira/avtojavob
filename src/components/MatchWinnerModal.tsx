import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { MatchState } from '../types';
import { sound } from '../utils/audio';
import { Trophy, Skull, RotateCcw } from 'lucide-react';

interface MatchWinnerModalProps {
  winner: 'player' | 'opponent' | null;
  matchState: MatchState;
  onPlayAgain: () => void;
}

export const MatchWinnerModal: React.FC<MatchWinnerModalProps> = ({
  winner,
  matchState,
  onPlayAgain
}) => {
  if (!winner) return null;

  const isPlayerWin = winner === 'player';

  useEffect(() => {
    if (isPlayerWin) {
      sound.playMatchVictory();
      // Fire confetti bursts
      const duration = 2.5 * 1000;
      const end = Date.now() + duration;

      const frame = () => {
        confetti({
          particleCount: 4,
          angle: 60,
          spread: 55,
          origin: { x: 0 },
          colors: ['#00e5ff', '#fae8ff', '#f59e0b', '#3b82f6']
        });
        confetti({
          particleCount: 4,
          angle: 120,
          spread: 55,
          origin: { x: 1 },
          colors: ['#00e5ff', '#fae8ff', '#f59e0b', '#3b82f6']
        });

        if (Date.now() < end) {
          requestAnimationFrame(frame);
        }
      };
      frame();
    } else {
      sound.playLose();
    }
  }, [isPlayerWin]);

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="relative w-full max-w-sm rounded-3xl bg-gradient-to-b from-slate-900 to-slate-950 border-2 border-slate-700/80 p-6 text-center shadow-[0_0_50px_rgba(0,0,0,0.8)] animate-scale-up">
        {/* Glow Header Icon */}
        <div className="mx-auto w-16 h-16 rounded-2xl flex items-center justify-center mb-4 shadow-xl border ${isPlayerWin ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_25px_#00e5ff]' : 'bg-red-500/20 border-red-500 text-red-400 shadow-[0_0_25px_#ef4444]'}">
          {isPlayerWin ? (
            <Trophy className="w-9 h-9 text-yellow-300 animate-bounce" />
          ) : (
            <Skull className="w-9 h-9 text-red-400" />
          )}
        </div>

        {/* Title */}
        <h2
          className={`text-3xl font-black italic tracking-wider mb-1 ${
            isPlayerWin
              ? 'text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 via-cyan-300 to-white drop-shadow-[0_0_20px_#00e5ff]'
              : 'text-red-500 drop-shadow-[0_0_15px_#ef4444]'
          }`}
        >
          {isPlayerWin ? 'GLORIOUS VICTORY!' : 'MATCH DEFEAT'}
        </h2>

        <p className="text-xs text-slate-400 mb-5 font-semibold">
          {isPlayerWin
            ? 'You conquered the arena in Best of 3!'
            : 'Nexus AI claimed 2 decisive points!'}
        </p>

        {/* Final Score Box */}
        <div className="bg-slate-950/80 rounded-2xl border border-slate-800 p-4 mb-5">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest block mb-1">
            FINAL MATCH SCORE
          </span>
          <div className="text-4xl font-black flex items-center justify-center gap-3">
            <span className="text-cyan-400 drop-shadow">{matchState.playerScore}</span>
            <span className="text-slate-600 text-2xl font-normal">-</span>
            <span className="text-amber-400 drop-shadow">{matchState.opponentScore}</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-2 block">
            {matchState.decisiveRounds} decisive round{matchState.decisiveRounds !== 1 ? 's' : ''} played
          </span>
        </div>

        {/* Play Again Button */}
        <button
          onClick={onPlayAgain}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-cyan-400 via-indigo-500 to-amber-400 hover:opacity-95 text-slate-950 font-black text-sm uppercase tracking-widest shadow-[0_0_25px_rgba(0,229,255,0.5)] active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
          PLAY AGAIN
        </button>
      </div>
    </div>
  );
};
