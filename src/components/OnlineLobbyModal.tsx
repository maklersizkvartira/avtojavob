import React, { useState } from 'react';
import { X, Users, Copy, Check, Play, Globe } from 'lucide-react';

interface OnlineLobbyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateRoom: (name: string) => void;
  onJoinRoom: (code: string, name: string) => void;
  roomCode: string | null;
  onlineCount: number;
}

export const OnlineLobbyModal: React.FC<OnlineLobbyModalProps> = ({
  isOpen,
  onClose,
  onCreateRoom,
  onJoinRoom,
  roomCode,
  onlineCount
}) => {
  const [playerName, setPlayerName] = useState('Player 1');
  const [inputCode, setInputCode] = useState('');
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (roomCode) {
      navigator.clipboard.writeText(roomCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="relative w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-700/80 p-5 sm:p-6 shadow-2xl animate-scale-up">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-indigo-400" />
            <h3 className="text-base font-extrabold text-white">LIVE 1V1 MULTIPLAYER</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Online Status Pill */}
        <div className="flex items-center justify-between bg-indigo-950/60 border border-indigo-800/40 px-3 py-2 rounded-xl mb-4 text-xs">
          <span className="text-indigo-300 font-medium">Railway Game Server</span>
          <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            {onlineCount || 1} Online
          </span>
        </div>

        {/* Nickname Input */}
        <div className="mb-4">
          <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
            YOUR FIGHTER NAME
          </label>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            maxLength={14}
            className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-bold text-sm focus:border-cyan-400 outline-none"
          />
        </div>

        {/* If room was created, show code and wait state */}
        {roomCode ? (
          <div className="bg-slate-950 p-4 rounded-2xl border border-cyan-500/30 text-center mb-4">
            <span className="text-[10px] text-cyan-400 uppercase font-black tracking-widest block mb-1">
              ROOM CREATED! SHARE CODE:
            </span>
            <div className="text-3xl font-black font-mono tracking-widest text-cyan-300 my-2">
              {roomCode}
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Waiting for your opponent to join with this code...
            </p>
            <button
              onClick={handleCopy}
              className="px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-400/50 text-cyan-300 text-xs font-bold flex items-center justify-center gap-1.5 mx-auto hover:bg-cyan-500/30 transition-all cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'CODE COPIED!' : 'COPY ROOM CODE'}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Create Room Button */}
            <button
              onClick={() => onCreateRoom(playerName)}
              className="w-full py-3 rounded-2xl bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-400 hover:to-cyan-400 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 cursor-pointer active:scale-95 transition-all"
            >
              <Users className="w-4 h-4" />
              CREATE NEW ROOM
            </button>

            {/* Divider */}
            <div className="flex items-center gap-2 text-slate-600 text-xs">
              <div className="flex-1 h-px bg-slate-800" />
              <span>OR JOIN ROOM</span>
              <div className="flex-1 h-px bg-slate-800" />
            </div>

            {/* Join Code input & button */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="4-LETTER CODE"
                value={inputCode}
                onChange={(e) => setInputCode(e.target.value.toUpperCase())}
                maxLength={6}
                className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono font-bold text-center tracking-widest text-sm focus:border-indigo-400 outline-none uppercase"
              />
              <button
                onClick={() => onJoinRoom(inputCode, playerName)}
                disabled={!inputCode.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold text-xs uppercase cursor-pointer"
              >
                JOIN
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
