import React, { useState } from 'react';
import { AVATARS, HAND_SKINS } from '../utils/shopData';
import { UserProfile, HandSkinId } from '../types';
import { sound } from '../utils/audio';
import { X, ShoppingBag, Check, Lock, Sparkles } from 'lucide-react';

interface ShopModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile;
  onUpdateProfile: (updated: UserProfile) => void;
}

export const ShopModal: React.FC<ShopModalProps> = ({
  isOpen,
  onClose,
  profile,
  onUpdateProfile
}) => {
  const [tab, setTab] = useState<'avatars' | 'hands'>('avatars');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const buyAvatar = (avatarId: string, price: number) => {
    if (profile.ownedAvatars.includes(avatarId)) {
      // Just equip
      sound.playTap();
      onUpdateProfile({ ...profile, selectedAvatar: avatarId });
      return;
    }

    if (profile.coins < price) {
      sound.playLose();
      setErrorMsg('Tangalar yetarli emas! O\'yinda g\'alaba qozonib pul ishlang.');
      setTimeout(() => setErrorMsg(null), 3000);
      return;
    }

    sound.playCoin();
    onUpdateProfile({
      ...profile,
      coins: profile.coins - price,
      ownedAvatars: [...profile.ownedAvatars, avatarId],
      selectedAvatar: avatarId
    });
  };

  const buyHandSkin = (skinId: HandSkinId, price: number) => {
    if (profile.ownedHandSkins.includes(skinId)) {
      // Just equip
      sound.playTap();
      onUpdateProfile({ ...profile, selectedHandSkin: skinId });
      return;
    }

    if (profile.coins < price) {
      sound.playLose();
      setErrorMsg('Tangalar yetarli emas! O\'yinda g\'alaba qozonib pul ishlang.');
      setTimeout(() => setErrorMsg(null), 3000);
      return;
    }

    sound.playCoin();
    onUpdateProfile({
      ...profile,
      coins: profile.coins - price,
      ownedHandSkins: [...profile.ownedHandSkins, skinId],
      selectedHandSkin: skinId
    });
  };

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-4 select-none">
      <div className="relative w-full max-w-md rounded-3xl bg-slate-900 border border-slate-700/80 p-5 shadow-2xl max-h-[90vh] flex flex-col animate-scale-up">
        {/* Header with Balance */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
          <div className="flex items-center gap-2">
            <ShoppingBag className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-extrabold text-white">DO'KON (SHOP)</h3>
          </div>

          <div className="flex items-center gap-2">
            {/* Coins Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 font-black text-xs shadow-sm">
              <span>🪙</span>
              <span>{profile.coins}</span>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Earning Tip */}
        <div className="flex items-center justify-between bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-xl text-[11px] text-slate-400 mb-3">
          <span className="flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Raund yutug'i: <b className="text-amber-300">+50</b> | Match yutug'i: <b className="text-amber-300">+150</b>
          </span>
        </div>

        {/* Tab Buttons */}
        <div className="grid grid-cols-2 gap-2 p-1 bg-slate-950 rounded-2xl mb-3 border border-slate-800">
          <button
            onClick={() => setTab('avatars')}
            className={`py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tab === 'avatars'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 shadow-md font-extrabold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🎭 Profil Rasmlari
          </button>
          <button
            onClick={() => setTab('hands')}
            className={`py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              tab === 'hands'
                ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-slate-950 shadow-md font-extrabold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🧤 Qo'l Stillari
          </button>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="mb-2 py-1.5 px-3 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 text-xs text-center font-bold animate-bounce">
            {errorMsg}
          </div>
        )}

        {/* Items List (Scrollable) */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {tab === 'avatars' ? (
            /* AVATARS LIST */
            <div className="grid grid-cols-2 gap-2.5">
              {AVATARS.map((item) => {
                const isOwned = profile.ownedAvatars.includes(item.id);
                const isEquipped = profile.selectedAvatar === item.id;

                return (
                  <div
                    key={item.id}
                    className={`flex flex-col items-center justify-between p-3 rounded-2xl border transition-all ${
                      isEquipped
                        ? 'bg-cyan-500/15 border-cyan-400 shadow-[0_0_15px_rgba(0,229,255,0.25)]'
                        : isOwned
                        ? 'bg-slate-950 border-slate-800 hover:border-slate-700'
                        : 'bg-slate-950/60 border-slate-800/80'
                    }`}
                  >
                    <div className="text-3xl my-1">{item.icon}</div>
                    <span className="text-xs font-bold text-slate-200 mb-1 text-center">
                      {item.name}
                    </span>

                    {/* Action Button */}
                    {isEquipped ? (
                      <span className="w-full py-1.5 rounded-xl bg-cyan-400/20 text-cyan-300 text-[11px] font-black flex items-center justify-center gap-1 border border-cyan-400/30">
                        <Check className="w-3.5 h-3.5" /> Tanlangan
                      </span>
                    ) : isOwned ? (
                      <button
                        onClick={() => buyAvatar(item.id, item.price)}
                        className="w-full py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold cursor-pointer"
                      >
                        Kiyish
                      </button>
                    ) : (
                      <button
                        onClick={() => buyAvatar(item.id, item.price)}
                        className="w-full py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-[11px] font-black flex items-center justify-center gap-1 cursor-pointer shadow-md"
                      >
                        <span>Sotib olish:</span>
                        <span>{item.price} 🪙</span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            /* HAND SKINS LIST */
            <div className="space-y-2.5">
              {HAND_SKINS.map((skin) => {
                const isOwned = profile.ownedHandSkins.includes(skin.id);
                const isEquipped = profile.selectedHandSkin === skin.id;

                return (
                  <div
                    key={skin.id}
                    className={`flex items-center justify-between p-3 rounded-2xl border transition-all ${
                      isEquipped
                        ? 'bg-amber-500/15 border-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.25)]'
                        : isOwned
                        ? 'bg-slate-950 border-slate-800 hover:border-slate-700'
                        : 'bg-slate-950/60 border-slate-800/80'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {/* Color swatch / icon */}
                      <div
                        className="w-11 h-11 rounded-2xl border flex items-center justify-center text-xl shadow-inner"
                        style={{
                          backgroundColor: skin.palmColor,
                          borderColor: skin.accentColor
                        }}
                      >
                        {skin.icon}
                      </div>

                      <div>
                        <h4 className="text-xs font-black text-white">{skin.name}</h4>
                        <p className="text-[10px] text-slate-400 max-w-[180px] leading-tight">
                          {skin.description}
                        </p>
                      </div>
                    </div>

                    {/* Action button */}
                    <div className="min-w-[90px] text-right">
                      {isEquipped ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-amber-400/20 text-amber-300 text-[11px] font-black border border-amber-400/30">
                          <Check className="w-3.5 h-3.5" /> Tanlangan
                        </span>
                      ) : isOwned ? (
                        <button
                          onClick={() => buyHandSkin(skin.id, skin.price)}
                          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold cursor-pointer"
                        >
                          Kiyish
                        </button>
                      ) : (
                        <button
                          onClick={() => buyHandSkin(skin.id, skin.price)}
                          className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-300 hover:to-orange-400 text-slate-950 text-[11px] font-black flex items-center justify-center gap-1 cursor-pointer shadow-md"
                        >
                          <Lock className="w-3 h-3" />
                          <span>{skin.price} 🪙</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
