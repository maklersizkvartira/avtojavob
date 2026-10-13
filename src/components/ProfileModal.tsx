import React, { useState } from 'react';
import { UserProfile } from '../types';
import { AVATARS } from '../utils/shopData';
import { sound } from '../utils/audio';
import { X, User, Edit2, Check, Award, Trophy } from 'lucide-react';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile;
  onUpdateProfile: (updated: UserProfile) => void;
  onOpenShop: () => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  profile,
  onUpdateProfile,
  onOpenShop
}) => {
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(profile.name);

  if (!isOpen) return null;

  const handleSaveName = () => {
    if (nameInput.trim()) {
      onUpdateProfile({ ...profile, name: nameInput.trim() });
    }
    setIsEditingName(false);
    sound.playTap();
  };

  const currentAvatar = AVATARS.find(a => a.id === profile.selectedAvatar) || AVATARS[0];
  const winRate = profile.totalMatches > 0
    ? Math.round((profile.totalWins / profile.totalMatches) * 100)
    : 0;

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4 select-none">
      <div className="relative w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-700/80 p-5 sm:p-6 shadow-2xl animate-scale-up">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-extrabold text-white">PROFIL</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Profile Card */}
        <div className="flex flex-col items-center text-center mb-5">
          {/* Avatar Icon */}
          <div className="relative">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border-2 border-cyan-400 flex items-center justify-center text-5xl shadow-[0_0_20px_rgba(0,229,255,0.3)]">
              {currentAvatar.icon}
            </div>
            <button
              onClick={() => {
                onClose();
                onOpenShop();
              }}
              className="absolute -bottom-1 -right-1 px-2 py-0.5 rounded-full bg-amber-500 text-slate-950 text-[10px] font-black border border-amber-300 shadow-md cursor-pointer hover:bg-amber-400"
              title="Avatarni o'zgartirish"
            >
              O'zgartirish
            </button>
          </div>

          {/* Name & Edit */}
          <div className="mt-3 flex items-center gap-2">
            {isEditingName ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  maxLength={15}
                  className="px-2.5 py-1 rounded-lg bg-slate-950 border border-cyan-400 text-white font-bold text-sm text-center outline-none"
                  autoFocus
                />
                <button
                  onClick={handleSaveName}
                  className="p-1 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <h4 className="text-lg font-black text-white">{profile.name}</h4>
                <button
                  onClick={() => setIsEditingName(true)}
                  className="text-slate-400 hover:text-cyan-300"
                  title="Ismni tahrirlash"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
          <span className="text-[11px] text-cyan-300 font-semibold mt-0.5">
            {currentAvatar.name}
          </span>
        </div>

        {/* Balance & Stats Grid */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              TANGALAR
            </span>
            <span className="text-base font-black text-amber-400 flex items-center justify-center gap-1">
              <span>🪙</span> {profile.coins}
            </span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              G'ALABALAR
            </span>
            <span className="text-base font-black text-cyan-400 flex items-center justify-center gap-1">
              <Trophy className="w-3.5 h-3.5" /> {profile.totalWins}
            </span>
          </div>

          <div className="bg-slate-950 p-2.5 rounded-2xl border border-slate-800 text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-0.5">
              G'ALABA %
            </span>
            <span className="text-base font-black text-emerald-400 flex items-center justify-center gap-1">
              <Award className="w-3.5 h-3.5" /> {winRate}%
            </span>
          </div>
        </div>

        {/* Shop Button Link */}
        <button
          onClick={() => {
            onClose();
            onOpenShop();
          }}
          className="w-full py-3 rounded-2xl bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 cursor-pointer transition-all"
        >
          <span>🛒 DO'KONGA O'TISH (RASMLAR & QO'LLAR)</span>
        </button>
      </div>
    </div>
  );
};
