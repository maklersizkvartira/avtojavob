import React, { useState } from 'react';
import { Volume2, VolumeX, RotateCcw, ShoppingBag } from 'lucide-react';
import { UserProfile } from '../types';
import { AVATARS } from '../utils/shopData';

interface TopBarProps {
  profile: UserProfile;
  isMuted: boolean;
  onToggleSound: () => void;
  onResetMatch: () => void;
  onOpenProfile: () => void;
  onOpenShop: () => void;
  matchInProgress: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  profile,
  isMuted,
  onToggleSound,
  onResetMatch,
  onOpenProfile,
  onOpenShop,
  matchInProgress
}) => {
  const [showConfirmReset, setShowConfirmReset] = useState(false);

  const currentAvatar = AVATARS.find(a => a.id === profile.selectedAvatar) || AVATARS[0];

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
    <header className="w-full max-w-xl mx-auto px-4 pt-3 pb-2 select-none">
      <div className="flex items-center justify-between gap-2">
        {/* Left: Player Profile Pill Button */}
        <button
          onClick={onOpenProfile}
          className="flex items-center gap-2 p-1.5 pr-3 rounded-2xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 transition-all cursor-pointer shadow-md text-left"
          title="Profilni ko'rish"
        >
          <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-400/60 flex items-center justify-center text-xl shadow-[0_0_10px_rgba(0,229,255,0.3)]">
            {currentAvatar.icon}
          </div>
          <div>
            <span className="text-xs font-black text-white block leading-tight">
              {profile.name}
            </span>
            <span className="text-[10px] text-cyan-300 font-semibold">
              Profil
            </span>
          </div>
        </button>

        {/* Center: Coins / Money Pill */}
        <button
          onClick={onOpenShop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-black transition-all cursor-pointer shadow-sm hover:scale-105"
          title="Do'kondan xarid qilish"
        >
          <span className="text-sm">🪙</span>
          <span>{profile.coins} tanga</span>
        </button>

        {/* Right: Shop, Sound, and Restart */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Shop Button */}
          <button
            onClick={onOpenShop}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-black text-xs transition-all shadow-[0_0_15px_rgba(251,191,36,0.35)] cursor-pointer active:scale-95"
            title="Do'kon: Rasmlar va Qo'llar"
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Do'kon</span>
          </button>

          {/* Sound Toggle */}
          <button
            onClick={onToggleSound}
            aria-label={isMuted ? 'Ovozni yoqish' : 'Ovozni o\'chirish'}
            className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-all cursor-pointer"
            title={isMuted ? 'Ovozni yoqish' : 'Ovozni o\'chirish'}
          >
            {isMuted ? (
              <VolumeX className="w-4 h-4 text-red-400" />
            ) : (
              <Volume2 className="w-4 h-4 text-cyan-400" />
            )}
          </button>

          {/* Reset Match */}
          <button
            onClick={handleResetClick}
            aria-label="O'yinni qayta boshlash"
            className="p-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-slate-400 hover:text-red-400 transition-all cursor-pointer"
            title="O'yinni qayta boshlash"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Confirmation Dialog for Reset */}
      {showConfirmReset && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl p-5 max-w-xs w-full text-center shadow-2xl animate-scale-up">
            <h3 className="text-base font-extrabold text-white mb-1.5">Matchni qayta boshlaysizmi?</h3>
            <p className="text-xs text-slate-400 mb-4">
              Joriy hisob va raundlar tarixi bekor qilinadi.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setShowConfirmReset(false)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 cursor-pointer"
              >
                Bekor qilish
              </button>
              <button
                onClick={confirmReset}
                className="flex-1 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-xs font-bold text-white shadow-lg cursor-pointer"
              >
                Qayta boshlash
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
