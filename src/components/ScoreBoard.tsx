import React from 'react';
import { MatchState } from '../types';

interface ScoreBoardProps {
  matchState: MatchState;
  lastOutcome: string | null;
}

export const ScoreBoard: React.FC<ScoreBoardProps> = ({ matchState, lastOutcome }) => {
  const { playerScore, opponentScore, decisiveRounds, history } = matchState;

  // Best of 3 slots (slot 1, slot 2, slot 3)
  const decisiveHistory = history.filter(h => h.isDecisive);

  return (
    <div className="w-full max-w-xl mx-auto px-4 py-2">
      {/* Main Score Glass Card */}
      <div className="relative rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-700/60 shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-md p-3.5 sm:p-4">
        {/* Top Header: Best of 3 Match Tracker */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-bold tracking-wider text-slate-400 uppercase">
              BEST OF 3
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 font-semibold border border-amber-500/20">
              FIRST TO 2 WINS
            </span>
          </div>

          {/* Decisive Rounds Progress Circles */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
              SLOT:
            </span>
            {[1, 2, 3].map((slot) => {
              const record = decisiveHistory[slot - 1];
              let slotClass = 'bg-slate-800 border-slate-700 text-slate-500';
              let label = `${slot}`;

              if (record) {
                if (record.outcome === 'win') {
                  slotClass = 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-[0_0_8px_#00e5ff]';
                  label = 'YOU';
                } else if (record.outcome === 'lose') {
                  slotClass = 'bg-amber-500/20 border-amber-400 text-amber-300 shadow-[0_0_8px_#ff9100]';
                  label = 'AI';
                }
              }

              return (
                <div
                  key={slot}
                  className={`w-7 h-7 rounded-lg border flex items-center justify-center text-[10px] font-black transition-all ${slotClass}`}
                  title={`Decisive Round Slot ${slot}`}
                >
                  {label}
                </div>
              );
            })}
          </div>
        </div>

        {/* Big Versus Scoreboard */}
        <div className="grid grid-cols-7 items-center">
          {/* Player Score Column */}
          <div className="col-span-3 flex flex-col items-start sm:items-center">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#00e5ff]" />
              <span className="text-xs sm:text-sm font-extrabold tracking-wide text-cyan-300">
                PLAYER
              </span>
            </div>
            <div className="text-4xl sm:text-5xl font-black text-cyan-400 drop-shadow-[0_0_15px_rgba(0,229,255,0.6)] my-0.5">
              {playerScore}
            </div>
            {/* Wins pips */}
            <div className="flex gap-1.5 mt-0.5">
              <div
                className={`w-3.5 h-1.5 rounded-full transition-all ${
                  playerScore >= 1 ? 'bg-cyan-400 shadow-[0_0_6px_#00e5ff]' : 'bg-slate-800'
                }`}
              />
              <div
                className={`w-3.5 h-1.5 rounded-full transition-all ${
                  playerScore >= 2 ? 'bg-cyan-400 shadow-[0_0_6px_#00e5ff]' : 'bg-slate-800'
                }`}
              />
            </div>
          </div>

          {/* VS Divider */}
          <div className="col-span-1 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-xs font-black text-slate-400 shadow-inner">
              VS
            </div>
          </div>

          {/* Opponent Score Column */}
          <div className="col-span-3 flex flex-col items-end sm:items-center">
            <div className="flex items-center gap-2">
              <span className="text-xs sm:text-sm font-extrabold tracking-wide text-amber-400">
                NEXUS AI
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_#ff9100]" />
            </div>
            <div className="text-4xl sm:text-5xl font-black text-amber-400 drop-shadow-[0_0_15px_rgba(255,145,0,0.6)] my-0.5">
              {opponentScore}
            </div>
            {/* Wins pips */}
            <div className="flex gap-1.5 mt-0.5">
              <div
                className={`w-3.5 h-1.5 rounded-full transition-all ${
                  opponentScore >= 1 ? 'bg-amber-400 shadow-[0_0_6px_#ff9100]' : 'bg-slate-800'
                }`}
              />
              <div
                className={`w-3.5 h-1.5 rounded-full transition-all ${
                  opponentScore >= 2 ? 'bg-amber-400 shadow-[0_0_6px_#ff9100]' : 'bg-slate-800'
                }`}
              />
            </div>
          </div>
        </div>

        {/* Draw Notification banner if last round was draw */}
        {lastOutcome === 'draw' && (
          <div className="mt-3 py-1.5 px-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-between text-xs text-amber-300">
            <span className="font-semibold flex items-center gap-1.5">
              <span>⚡</span> DRAW OCCURRED!
            </span>
            <span className="text-[11px] text-amber-200/80">
              Draws do not award points. Replaying round slot.
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
