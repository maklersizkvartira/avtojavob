import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';
import { MatchState } from '../types';
import { sound } from '../utils/audio';
import { Trophy, Skull, RotateCcw } from 'lucide-react';

interface MatchWinnerModalProps {
  winner: 'player' | 'opponent' | null;
  matchState: MatchState;
  onPlayAgain: () => void;
  earnedCoins: number;
}

export const MatchWinnerModal: React.FC<MatchWinnerModalProps> = ({
  winner,
  matchState,
  onPlayAgain,
  earnedCoins
}) => {
  if (!winner) return null;

  const isPlayerWin = winner === 'player';

  useEffect(() => {
    if (isPlayerWin) {
      sound.playMatchVictory();
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#00e5ff', '#ffd700', '#f59e0b', '#3b82f6']
      });
    } else {
      sound.playLose();
    }
  }, [isPlayerWin]);

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4 select-none">
      <div className="relative w-full max-w-sm rounded-3xl bg-slate-900 border-2 border-slate-700/80 p-6 text-center shadow-[0_0_50px_rgba(0,0,0,0.8)] animate-scale-up">
        {/* Glow Header Icon */}
        <div className={`mx-auto w-16 h-16 rounded-2xl flex items-center justify-center mb-4 shadow-xl border ${
          isPlayerWin
            ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_25px_#00e5ff]'
            : 'bg-red-500/20 border-red-500 text-red-400 shadow-[0_0_25px_#ef4444]'
        }`}>
          {isPlayerWin ? (
            <Trophy className="w-9 h-9 text-yellow-300 animate-bounce" />
          ) : (
            <Skull className="w-9 h-9 text-red-400" />
          )}
        </div>

        {/* Title */}
        <h2 className={`text-2xl font-black italic tracking-wider mb-1 ${
          isPlayerWin
            ? 'text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 via-cyan-300 to-white drop-shadow-[0_0_20px_#00e5ff]'
            : 'text-red-500 drop-shadow-[0_0_15px_#ef4444]'
        }`}>
          {isPlayerWin ? 'MATCH G\'OLIBI! 🏆' : 'KOMPYUTER YUTDI 💥'}
        </h2>

        <p className="text-xs text-slate-400 mb-4 font-semibold">
          {isPlayerWin
            ? 'Siz 2 ochko to\'plab, matchda g\'alaba qozondingiz!'
            : 'Kompyuter 2 ta hal qiluvchi ochkoni qo\'lga kiritdi!'}
        </p>

        {/* Reward Box */}
        {isPlayerWin && (
          <div className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-sm font-black mb-4">
            <span>Yutuq:</span>
            <span>+{earnedCoins} tanga 🪙</span>
          </div>
        )}

        {/* Final Score Box */}
        <div className="bg-slate-950/80 rounded-2xl border border-slate-800 p-4 mb-5">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest block mb-1">
            YAKUNIY HISOB
          </span>
          <div className="text-4xl font-black flex items-center justify-center gap-3">
            <span className="text-cyan-400 drop-shadow">{matchState.playerScore}</span>
            <span className="text-slate-600 text-2xl font-normal">:</span>
            <span className="text-amber-400 drop-shadow">{matchState.opponentScore}</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-2 block">
            {matchState.decisiveRounds} ta hal qiluvchi raund o'ynaldi
          </span>
        </div>

        {/* Play Again Button */}
        <button
          onClick={onPlayAgain}
          className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-cyan-400 to-blue-500 hover:opacity-95 text-slate-950 font-black text-sm uppercase tracking-widest shadow-[0_0_25px_rgba(0,229,255,0.4)] active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
          YANA O'YNASH
        </button>
      </div>
    </div>
  );
};
