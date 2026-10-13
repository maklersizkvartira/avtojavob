import React from 'react';
import { RoundOutcome, HandChoice } from '../types';
import { getRoundOutcomeDescription } from '../utils/gameLogic';

interface ResultBannerProps {
  outcome: RoundOutcome | null;
  playerChoice: HandChoice | null;
  opponentChoice: HandChoice | null;
  onNextRound: () => void;
  isMatchOver: boolean;
}

export const ResultBanner: React.FC<ResultBannerProps> = ({
  outcome,
  playerChoice,
  opponentChoice,
  onNextRound,
  isMatchOver
}) => {
  if (!outcome || isMatchOver) return null;

  const desc = playerChoice && opponentChoice
    ? getRoundOutcomeDescription(playerChoice, opponentChoice)
    : '';

  let title = 'ROUND WON!';
  let titleColor = 'text-cyan-300 drop-shadow-[0_0_15px_#00e5ff]';
  let badgeColor = 'bg-cyan-500/20 border-cyan-400 text-cyan-300';

  if (outcome === 'lose') {
    title = 'ROUND LOST!';
    titleColor = 'text-amber-400 drop-shadow-[0_0_15px_#ff9100]';
    badgeColor = 'bg-amber-500/20 border-amber-400 text-amber-300';
  } else if (outcome === 'draw') {
    title = 'DRAW!';
    titleColor = 'text-purple-300 drop-shadow-[0_0_15px_#c084fc]';
    badgeColor = 'bg-purple-500/20 border-purple-400 text-purple-300';
  }

  return (
    <div className="w-full max-w-md mx-auto px-4 mt-1 mb-2 animate-bounce-short">
      <div className="relative rounded-2xl bg-slate-900/95 border border-slate-700/80 p-3.5 sm:p-4 text-center shadow-2xl backdrop-blur-md">
        <div className="inline-block px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border mb-1.5 ${badgeColor}">
          {outcome === 'draw' ? 'ROUND IMPASSE' : 'ROUND RESOLVED'}
        </div>

        <h2 className={`text-2xl sm:text-3xl font-black italic tracking-wide mb-1 ${titleColor}`}>
          {title}
        </h2>

        <p className="text-xs sm:text-sm text-slate-300 font-medium mb-3">
          {desc}
        </p>

        {outcome === 'draw' && (
          <p className="text-[11px] text-amber-300/90 mb-3 bg-amber-500/10 py-1 px-2 rounded-lg border border-amber-500/20">
            Draw does not award points. You can retry this round slot.
          </p>
        )}

        <button
          onClick={onNextRound}
          className="w-full py-2.5 sm:py-3 rounded-xl bg-gradient-to-r from-cyan-500 via-indigo-600 to-amber-500 hover:from-cyan-400 hover:to-amber-400 text-slate-950 font-black text-sm uppercase tracking-wider shadow-[0_0_20px_rgba(0,229,255,0.4)] active:scale-95 transition-all cursor-pointer"
        >
          {outcome === 'draw' ? 'RETRY ROUND' : 'NEXT ROUND'} →
        </button>
      </div>
    </div>
  );
};
