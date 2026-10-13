import React from 'react';
import { HandChoice, HandSkin } from '../types';
import { HandCard3D } from './HandCard3D';

interface ArenaCardsProps {
  playerChoice: HandChoice | null;
  opponentChoice: HandChoice | null;
  playerScore: number;
  opponentScore: number;
  currentRound: number;
  playerName: string;
  playerHandSkin: HandSkin;
  isShaking: boolean;
}

export const ArenaCards: React.FC<ArenaCardsProps> = ({
  playerChoice,
  opponentChoice,
  playerScore,
  opponentScore,
  currentRound,
  playerName,
  playerHandSkin,
  isShaking
}) => {
  // Classic opponent hand
  const opponentHandSkin: HandSkin = {
    id: 'classic',
    name: 'Kompyuter',
    price: 0,
    description: '',
    palmColor: '#ffd0b0',
    sleeveColor: '#ffffff',
    accentColor: '#38bdf8',
    glowColor: 'rgba(56, 189, 248, 0.4)',
    icon: '🤖'
  };

  return (
    <div className="w-full max-w-xl mx-auto px-4 py-2">
      <div className="grid grid-cols-7 items-center gap-2">
        {/* Left: Player Hand Card */}
        <div className="col-span-3">
          <HandCard3D
            choice={playerChoice}
            label={playerName || 'Sen'}
            score={playerScore}
            isPlayer={true}
            handSkin={playerHandSkin}
            isShaking={isShaking}
          />
        </div>

        {/* Center: VS and Round Badge */}
        <div className="col-span-1 flex flex-col items-center justify-center text-center">
          <span className="text-sm sm:text-base font-black tracking-widest text-slate-300 drop-shadow">
            VS
          </span>
          <span className="text-[10px] sm:text-xs font-bold text-slate-400 mt-1 whitespace-nowrap">
            {currentRound}-raund
          </span>
        </div>

        {/* Right: Computer Hand Card */}
        <div className="col-span-3">
          <HandCard3D
            choice={opponentChoice}
            label="Kompyuter"
            score={opponentScore}
            isPlayer={false}
            handSkin={opponentHandSkin}
            isShaking={isShaking}
          />
        </div>
      </div>
    </div>
  );
};
