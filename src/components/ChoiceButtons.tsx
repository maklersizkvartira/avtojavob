import React from 'react';
import { HandChoice } from '../types';

interface ChoiceButtonsProps {
  selectedChoice: HandChoice;
  onSelectChoice: (choice: HandChoice) => void;
  onPlayRound: () => void;
  isPlaying: boolean;
}

export const ChoiceButtons: React.FC<ChoiceButtonsProps> = ({
  selectedChoice,
  onSelectChoice,
  onPlayRound,
  isPlaying
}) => {
  const choices: { id: HandChoice; label: string; icon: string }[] = [
    { id: 'rock', label: 'Tosh', icon: '✊' },
    { id: 'paper', label: 'Qog\'oz', icon: '✋' },
    { id: 'scissors', label: 'Qaychi', icon: '✌️' }
  ];

  return (
    <div className="w-full max-w-xl mx-auto px-4 mt-3 mb-4 select-none">
      {/* Title */}
      <div className="mb-2.5">
        <span className="text-xs sm:text-sm font-bold text-slate-300">
          Tanlovni o'zing sinab ko'r:
        </span>
      </div>

      {/* Choice Buttons Row */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-3">
        {choices.map((c) => {
          const isSelected = selectedChoice === c.id;

          return (
            <button
              key={c.id}
              onClick={() => onSelectChoice(c.id)}
              disabled={isPlaying}
              className={`flex flex-col items-center justify-center py-3 sm:py-3.5 px-2 rounded-2xl border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-[#2b354b] border-cyan-400 text-white shadow-[0_0_15px_rgba(0,229,255,0.3)] scale-[1.02]'
                  : 'bg-slate-900/80 hover:bg-slate-800/90 border-slate-700/80 text-slate-300 hover:text-white'
              } ${isPlaying ? 'opacity-60 cursor-not-allowed' : ''}`}
            >
              <span className="text-2xl sm:text-3xl mb-1">{c.icon}</span>
              <span className="text-xs sm:text-sm font-extrabold tracking-wide">
                {c.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Raundni O'yna Action Button */}
      <button
        onClick={onPlayRound}
        disabled={isPlaying}
        className={`w-full py-3.5 rounded-2xl font-black text-sm uppercase tracking-wider transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer ${
          isPlaying
            ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
            : 'bg-gradient-to-r from-slate-800 via-[#232c3d] to-slate-800 hover:from-cyan-600 hover:via-blue-600 hover:to-cyan-600 border border-slate-600 text-white hover:text-white hover:border-cyan-400 shadow-[0_0_20px_rgba(0,0,0,0.4)] active:scale-[0.98]'
        }`}
      >
        <span>Raundni o'yna</span>
        <span className="text-base">⚡</span>
      </button>
    </div>
  );
};
