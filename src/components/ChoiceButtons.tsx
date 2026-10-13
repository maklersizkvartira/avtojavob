import React from 'react';
import { HandChoice, GamePhase } from '../types';

interface ChoiceButtonsProps {
  onSelectChoice: (choice: HandChoice) => void;
  selectedChoice: HandChoice | null;
  phase: GamePhase;
}

export const ChoiceButtons: React.FC<ChoiceButtonsProps> = ({
  onSelectChoice,
  selectedChoice,
  phase
}) => {
  const isDisabled = phase !== 'ready';

  const choices: { id: HandChoice; label: string; keyHint: string; subtitle: string; icon: React.ReactNode }[] = [
    {
      id: 'rock',
      label: 'ROCK',
      keyHint: '1 / R',
      subtitle: 'Beats Scissors',
      icon: (
        <svg viewBox="0 0 24 24" className="w-8 h-8 sm:w-10 sm:h-10 fill-current" aria-hidden="true">
          {/* Detailed stylized fist icon */}
          <path d="M12 2C9.5 2 7.8 3.5 7.4 5.2C6.2 5.5 5 6.8 5 8.5C5 9.1 5.2 9.7 5.5 10.2C4.6 10.8 4 12 4 13.5C4 16.5 6.5 19 9.5 19H13C16.3 19 19 16.3 19 13V9C19 6.8 17.2 5 15 5C14.7 5 14.3 5.05 14 5.15C13.6 3.3 12 2 12 2ZM9 7C9.6 7 10 7.4 10 8V12H8V8.5C8 7.7 8.4 7 9 7ZM12 6C12.6 6 13 6.4 13 7V12H11V7C11 6.4 11.4 6 12 6ZM15 7C15.6 7 16 7.4 16 8V12H14V8C14 7.4 14.4 7 15 7Z" />
        </svg>
      )
    },
    {
      id: 'paper',
      label: 'PAPER',
      keyHint: '2 / P',
      subtitle: 'Beats Rock',
      icon: (
        <svg viewBox="0 0 24 24" className="w-8 h-8 sm:w-10 sm:h-10 fill-current" aria-hidden="true">
          {/* Detailed stylized open hand / palm icon */}
          <path d="M13 1.5C12.2 1.5 11.5 2.2 11.5 3V9.5H10.5V1C9.7 1 9 1.7 9 2.5V9.5H8V3C7.2 3 6.5 3.7 6.5 4.5V11H5.5V6C4.7 6 4 6.7 4 7.5V14.5C4 18.6 7.4 22 11.5 22H13.5C17.6 22 21 18.6 21 14.5V9C21 8.2 20.3 7.5 19.5 7.5C18.7 7.5 18 8.2 18 9V11H17V4C17 3.2 16.3 2.5 15.5 2.5C14.7 2.5 14 3.2 14 4V9.5H13V1.5Z" />
        </svg>
      )
    },
    {
      id: 'scissors',
      label: 'SCISSORS',
      keyHint: '3 / S',
      subtitle: 'Beats Paper',
      icon: (
        <svg viewBox="0 0 24 24" className="w-8 h-8 sm:w-10 sm:h-10 fill-current" aria-hidden="true">
          {/* Detailed scissors gesture / V sign icon */}
          <path d="M10 2C9.2 2 8.5 2.7 8.5 3.5V9.8L7.5 8.8C6.9 8.2 6 8.2 5.4 8.8C4.9 9.3 4.9 10.3 5.4 10.8L9 14.5V19C9 20.7 10.3 22 12 22H14C15.7 22 17 20.7 17 19V11.5C17 10.7 16.3 10 15.5 10C14.7 10 14 10.7 14 11.5V13H13V3.5C13 2.7 12.3 2 11.5 2C10.7 2 10 2.7 10 3.5V8.5H11.5V3.5C11.5 3.5 11.5 2 10 2Z" />
        </svg>
      )
    }
  ];

  return (
    <div className="w-full max-w-xl mx-auto px-4 pb-4">
      {/* Choice Prompt Header */}
      <div className="text-center mb-2.5">
        <span
          className={`text-xs sm:text-sm font-extrabold uppercase tracking-widest transition-colors ${
            isDisabled
              ? 'text-slate-500'
              : 'text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-white to-amber-400 animate-pulse'
          }`}
        >
          {phase === 'ready' ? '⚡ CHOOSE YOUR WEAPON ⚡' : 'ROUND LOCKED IN...'}
        </span>
      </div>

      {/* Button Row */}
      <div className="grid grid-cols-3 gap-2.5 sm:gap-4">
        {choices.map((choice) => {
          const isSelected = selectedChoice === choice.id;

          return (
            <button
              key={choice.id}
              id={`choice-btn-${choice.id}`}
              onClick={() => onSelectChoice(choice.id)}
              disabled={isDisabled}
              aria-label={`Select ${choice.label}`}
              className={`group relative flex flex-col items-center justify-between p-3 sm:p-4 rounded-2xl border-2 transition-all duration-200 select-none min-h-[96px] sm:min-h-[115px] ${
                isDisabled
                  ? isSelected
                    ? 'bg-cyan-950/70 border-cyan-400 text-cyan-300 shadow-[0_0_20px_rgba(0,229,255,0.4)] scale-105'
                    : 'bg-slate-900/40 border-slate-800 text-slate-600 opacity-60 cursor-not-allowed'
                  : 'bg-gradient-to-b from-slate-800/90 to-slate-900/95 border-slate-700/80 text-slate-200 hover:border-cyan-400/80 hover:text-cyan-300 hover:shadow-[0_0_25px_rgba(0,229,255,0.3)] active:scale-95 cursor-pointer shadow-lg'
              }`}
            >
              {/* Keyboard Hotkey Badge */}
              <span className="absolute top-2 right-2 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-950/60 border border-slate-700/60 text-slate-400 group-hover:text-cyan-300 group-hover:border-cyan-500/40">
                {choice.keyHint}
              </span>

              {/* Icon Container */}
              <div
                className={`transition-transform duration-200 ${
                  isDisabled
                    ? isSelected
                      ? 'scale-110 text-cyan-300'
                      : 'text-slate-600'
                    : 'group-hover:scale-110 group-hover:text-cyan-300 text-slate-300'
                }`}
              >
                {choice.icon}
              </div>

              {/* Labels */}
              <div className="flex flex-col items-center text-center mt-1">
                <span className="text-xs sm:text-sm font-black tracking-wider">
                  {choice.label}
                </span>
                <span className="text-[9px] text-slate-400 sm:block hidden mt-0.5">
                  {choice.subtitle}
                </span>
              </div>

              {/* Glowing Bottom Accent Strip */}
              <div
                className={`absolute bottom-0 left-4 right-4 h-0.5 rounded-full transition-all ${
                  isSelected
                    ? 'bg-cyan-400 shadow-[0_0_8px_#00e5ff]'
                    : 'bg-transparent group-hover:bg-cyan-500/50'
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
};
