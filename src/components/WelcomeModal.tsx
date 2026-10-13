import React, { useState } from 'react';
import { AVATARS } from '../utils/shopData';
import { sound } from '../utils/audio';
import { Sparkles } from 'lucide-react';

interface WelcomeModalProps {
  isOpen: boolean;
  onComplete: (name: string, avatar: string) => void;
}

export const WelcomeModal: React.FC<WelcomeModalProps> = ({ isOpen, onComplete }) => {
  const [name, setName] = useState('');
  const [selectedAvatar, setSelectedAvatar] = useState('avatar_boy');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim() || 'O\'yinchi';
    sound.playCoin();
    onComplete(cleanName, selectedAvatar);
  };

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="relative w-full max-w-sm rounded-3xl bg-slate-900 border-2 border-cyan-500/40 p-6 text-center shadow-[0_0_50px_rgba(0,229,255,0.3)] animate-scale-up">
        {/* Header Icon */}
        <div className="w-16 h-16 rounded-2xl bg-cyan-500/20 border border-cyan-400 mx-auto flex items-center justify-center mb-4 text-3xl shadow-[0_0_20px_#00e5ff]">
          🎮
        </div>

        <h2 className="text-2xl font-black text-white mb-1">
          Xush kelibsiz!
        </h2>
        <p className="text-xs text-slate-400 mb-4">
          O'yinni boshlash uchun ismingiz va profil rasmingizni tanlang:
        </p>

        {/* Bonus Coin Announcement */}
        <div className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold mb-4">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <span>Boshlang'ich sovg'a: <b>+200 tanga</b> 🪙</span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name Input */}
          <div className="text-left">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              Ismingiz:
            </label>
            <input
              type="text"
              required
              placeholder="Masalan: Sardor, Ali..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={15}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white font-bold text-sm focus:border-cyan-400 outline-none"
            />
          </div>

          {/* Avatar Selector */}
          <div className="text-left">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
              Boshlang'ich profil rasmi:
            </label>
            <div className="grid grid-cols-4 gap-2">
              {AVATARS.slice(0, 4).map((av) => (
                <button
                  type="button"
                  key={av.id}
                  onClick={() => setSelectedAvatar(av.id)}
                  className={`p-2.5 rounded-xl border text-2xl transition-all cursor-pointer ${
                    selectedAvatar === av.id
                      ? 'bg-cyan-500/20 border-cyan-400 shadow-[0_0_12px_#00e5ff] scale-105'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {av.icon}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 font-black text-sm uppercase tracking-wider shadow-[0_0_20px_rgba(0,229,255,0.4)] active:scale-95 transition-all cursor-pointer mt-2"
          >
            O'YINNI BOSHLASH 🚀
          </button>
        </form>
      </div>
    </div>
  );
};
