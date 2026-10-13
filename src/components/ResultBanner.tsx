import React from 'react';
import { RoundOutcome, HandChoice } from '../types';

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

  const choiceNames: Record<HandChoice, string> = {
    rock: 'Tosh',
    paper: 'Qog\'oz',
    scissors: 'Qaychi'
  };

  const pName = playerChoice ? choiceNames[playerChoice] : '';
  const opName = opponentChoice ? choiceNames[opponentChoice] : '';

  let title = 'RAUND G\'ALABASI! 🎉';
  let titleColor = 'text-cyan-300 drop-shadow-[0_0_12px_#00e5ff]';
  let badge = 'Siz yutdingiz (+50 tanga 🪙)';
  let desc = `${pName} ${opName}dan ustun keldi!`;

  if (outcome === 'lose') {
    title = 'RAUND MAG\'LUBIYATI 💥';
    titleColor = 'text-amber-400 drop-shadow-[0_0_12px_#ff9100]';
    badge = 'Kompyuter yutdi (+10 tanga 🪙)';
    desc = `Kompyuterning ${opName}i sizning ${pName}ingizdan ustun keldi.`;
  } else if (outcome === 'draw') {
    title = 'DURANG! 🤝';
    titleColor = 'text-purple-300 drop-shadow-[0_0_12px_#c084fc]';
    badge = 'Ochko berilmadi';
    desc = `Ikkala tomon ham ${pName} tanladi. Raund qayta o'ynaladi!`;
  }

  return (
    <div className="w-full max-w-xl mx-auto px-4 mt-1 mb-2 animate-bounce-short select-none">
      <div className="relative rounded-2xl bg-slate-900/95 border border-slate-700/80 p-3 sm:p-4 text-center shadow-xl backdrop-blur-md">
        <div className="inline-block px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700 mb-1.5">
          {badge}
        </div>

        <h2 className={`text-xl sm:text-2xl font-black italic tracking-wide mb-1 ${titleColor}`}>
          {title}
        </h2>

        <p className="text-xs text-slate-300 font-medium mb-3">
          {desc}
        </p>

        <button
          onClick={onNextRound}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg active:scale-95 transition-all cursor-pointer"
        >
          {outcome === 'draw' ? 'QAYTA O\'YNASH' : 'KEYINGI RAUND'} →
        </button>
      </div>
    </div>
  );
};
