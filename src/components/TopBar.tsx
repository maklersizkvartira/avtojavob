import React, { useState } from 'react';
import { Volume2, VolumeX, RotateCcw, BarChart2, Users, Shield } from 'lucide-react';
import { AIDifficulty, GameMode } from '../types';

interface TopBarProps {
  isMuted: boolean;
  onToggleSound: () => void;
  onResetMatch: () => void;
  difficulty: AIDifficulty;
  onChangeDifficulty: (diff: AIDifficulty) => void;
  gameMode: GameMode;
  onOpenOnlineLobby: () => void;
  onOpenStats: () => void;
  matchInProgress: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  isMuted,
  onToggleSound,
  onResetMatch,
  difficulty,
  onChangeDifficulty,
  gameMode,
  onOpenOnlineLobby,
  onOpenStats,
  matchInProgress
}) => {
  const [showConfirmReset, setShowConfirmReset] = useState(false);

  const handleResetClick = () => {
    if (matchInProgress) {
      setShowConfirmReset(true);
    } else {
      onResetMatch();
    }
  };

  const confirmReset = () => {
    setShowConfirmReset(false);
    onResetMatch();
  };

  return (
    <header className="w-full max-w-4xl mx-auto px-4 pt-3 pb-1 select-none">
      <div className="flex items-center justify-between gap-2">
        {/* Logo and Title */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-amber-500 p-0.5 shadow-[0_0_15px_rgba(0,229,255,0.4)] flex items-center justify-center">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <span className="text-sm font-black text-cyan-400">HG</span>
            </div>
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-black tracking-wider leading-none text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-amber-400">
              HANDS OF GLORY
            </h1>
            <span className="text-[10px] text-slate-400 tracking-widest uppercase font-semibold">
              3D CYBER ARENA
            </span>
          </div>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Difficulty Dropdown / Pill (when playing AI) */}
          {gameMode === 'ai' && (
            <div className="relative group">
              <button
                type="button"
                className="px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-[11px] font-bold text-slate-300 flex items-center gap-1 shadow-sm transition-all"
                title="Select AI Difficulty"
              >
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                <span className="capitalize hidden sm:inline">{difficulty}</span>
              </button>
              <div className="absolute right-0 top-full mt-1 hidden group-hover:flex flex-col bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-1 z-50 min-w-[110px]">
                {(['novice', 'tactical', 'grandmaster'] as AIDifficulty[]).map((d) => (
                  <button
                    key={d}
                    onClick={() => onChangeDifficulty(d)}
                    className={`px-2.5 py-1 text-left text-xs rounded capitalize font-medium transition-colors ${
                      difficulty === d
                        ? 'bg-cyan-500/20 text-cyan-300 font-bold'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Online Multiplayer Lobby Button */}
          <button
            onClick={onOpenOnlineLobby}
            aria-label="Online Multiplayer"
            className="p-1.5 sm:px-2.5 sm:py-1 rounded-lg bg-indigo-950/80 hover:bg-indigo-900/80 border border-indigo-700/70 text-indigo-300 hover:text-indigo-200 transition-all shadow-[0_0_10px_rgba(99,102,241,0.25)] flex items-center gap-1"
            title="Online 1v1 Mode"
          >
            <Users className="w-4 h-4 text-indigo-400" />
            <span className="text-[11px] font-bold hidden md:inline">1v1 Online</span>
          </button>

          {/* Stats Button */}
          <button
            onClick={onOpenStats}
            aria-label="View Stats"
            className="p-1.5 sm:p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-all"
            title="Statistics & Leaderboard"
          >
            <BarChart2 className="w-4 h-4 text-amber-400" />
          </button>

          {/* Sound Toggle */}
          <button
            onClick={onToggleSound}
            aria-label={isMuted ? 'Unmute Sound' : 'Mute Sound'}
            className="p-1.5 sm:p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-all"
            title={isMuted ? 'Unmute Sound' : 'Mute Sound'}
          >
            {isMuted ? (
              <VolumeX className="w-4 h-4 text-red-400" />
            ) : (
              <Volume2 className="w-4 h-4 text-cyan-400" />
            )}
          </button>

          {/* Reset Match Button */}
          <button
            onClick={handleResetClick}
            aria-label="Restart Match"
            className="p-1.5 sm:p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-red-300 transition-all"
            title="Restart Match"
          >
            <RotateCcw className="w-4 h-4 text-slate-400 hover:text-red-400" />
          </button>
        </div>
      </div>

      {/* Confirmation Dialog for Reset if match is ongoing */}
      {showConfirmReset && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 max-w-xs w-full text-center shadow-2xl animate-scale-up">
            <h3 className="text-base font-extrabold text-white mb-2">Restart Current Match?</h3>
            <p className="text-xs text-slate-400 mb-4">
              A match is currently in progress. Resetting will clear the score and round history.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setShowConfirmReset(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmReset}
                className="flex-1 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-xs font-bold text-white shadow-lg"
              >
                Restart
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
