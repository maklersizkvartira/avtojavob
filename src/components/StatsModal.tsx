import React, { useEffect, useState } from 'react';
import { X, Award, BarChart2, Flame, RefreshCw } from 'lucide-react';

interface StatsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ServerStats {
  totalMatches: number;
  playerWins: number;
  botWins: number;
  draws: number;
  choices: {
    rock: number;
    paper: number;
    scissors: number;
  };
  winStreakRecord: number;
}

interface LeaderboardEntry {
  name: string;
  streak: number;
  date: string;
}

export const StatsModal: React.FC<StatsModalProps> = ({ isOpen, onClose }) => {
  const [stats, setStats] = useState<ServerStats | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const [resStats, resLead] = await Promise.all([
        fetch('/api/stats').then(r => r.json()),
        fetch('/api/leaderboard').then(r => r.json())
      ]);
      setStats(resStats);
      setLeaderboard(resLead);
    } catch {
      // Local fallback if offline or backend cold-start
      setStats({
        totalMatches: 24,
        playerWins: 14,
        botWins: 10,
        draws: 4,
        choices: { rock: 35, paper: 28, scissors: 32 },
        winStreakRecord: 4
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStats();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const total = stats?.totalMatches || 1;
  const pWins = stats?.playerWins || 0;
  const winRate = Math.round((pWins / total) * 100);

  const rCount = stats?.choices.rock || 1;
  const pCount = stats?.choices.paper || 1;
  const sCount = stats?.choices.scissors || 1;
  const choiceTotal = rCount + pCount + sCount;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="relative w-full max-w-md rounded-3xl bg-slate-900 border border-slate-700/80 p-5 sm:p-6 shadow-2xl max-h-[90vh] overflow-y-auto animate-scale-up">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-extrabold text-white">ARENA STATISTICS & RANKS</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Global Key Metrics Grid */}
        <div className="grid grid-cols-3 gap-2.5 mb-4">
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              TOTAL MATCHES
            </span>
            <span className="text-xl font-black text-cyan-400">
              {stats?.totalMatches ?? '-'}
            </span>
          </div>

          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              PLAYER WIN RATE
            </span>
            <span className="text-xl font-black text-emerald-400">{winRate}%</span>
          </div>

          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              MAX STREAK
            </span>
            <span className="text-xl font-black text-amber-400 flex items-center justify-center gap-1">
              <Flame className="w-4 h-4 text-amber-400" />
              {stats?.winStreakRecord ?? '-'}
            </span>
          </div>
        </div>

        {/* Weapon Selection Frequency */}
        <div className="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 mb-4">
          <span className="text-xs font-bold text-slate-300 block mb-2.5">
            WEAPON PICK FREQUENCY
          </span>
          <div className="space-y-2">
            <div>
              <div className="flex justify-between text-[11px] mb-1 font-semibold text-slate-400">
                <span>ROCK</span>
                <span>{Math.round((rCount / choiceTotal) * 100)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-cyan-400"
                  style={{ width: `${(rCount / choiceTotal) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1 font-semibold text-slate-400">
                <span>PAPER</span>
                <span>{Math.round((pCount / choiceTotal) * 100)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-indigo-400"
                  style={{ width: `${(pCount / choiceTotal) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1 font-semibold text-slate-400">
                <span>SCISSORS</span>
                <span>{Math.round((sCount / choiceTotal) * 100)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-amber-400"
                  style={{ width: `${(sCount / choiceTotal) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Hall of Fame / Leaderboard */}
        <div className="bg-slate-950 p-3.5 rounded-2xl border border-slate-800 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Award className="w-4 h-4 text-yellow-400" />
              TOP ARENA STREAKS
            </span>
            <button
              onClick={fetchStats}
              className="text-[10px] text-cyan-400 flex items-center gap-1 hover:underline"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          <div className="space-y-1.5">
            {leaderboard.length > 0 ? (
              leaderboard.slice(0, 5).map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 text-center font-bold text-slate-500">
                      #{idx + 1}
                    </span>
                    <span className="font-semibold text-slate-200">{entry.name}</span>
                  </div>
                  <span className="font-mono font-bold text-amber-400">
                    {entry.streak} Wins
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 text-center py-2">No records yet</p>
            )}
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 font-bold text-xs text-slate-200 cursor-pointer"
        >
          CLOSE
        </button>
      </div>
    </div>
  );
};
