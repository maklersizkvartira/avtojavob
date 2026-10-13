import { AvatarItem, HandSkin, HandSkinId } from '../types';

export const AVATARS: AvatarItem[] = [
  { id: 'avatar_boy', name: 'Oddiy Bola', price: 0, icon: '🧒' },
  { id: 'avatar_ninja', name: 'Kulgili Ninja', price: 100, icon: '🥷' },
  { id: 'avatar_robot', name: 'Kiber Robot', price: 200, icon: '🤖' },
  { id: 'avatar_lion', name: 'Qahramon Sher', price: 350, icon: '🦁' },
  { id: 'avatar_king', name: 'Oltin Qirol', price: 500, icon: '👑' },
  { id: 'avatar_wizard', name: 'Sehrgar Bobo', price: 750, icon: '🧙‍♂️' },
  { id: 'avatar_alien', name: 'Kosmik Fazogir', price: 1000, icon: '👽' },
  { id: 'avatar_diamond', name: 'Olmos Afsona', price: 1500, icon: '💎' }
];

export const HAND_SKINS: HandSkin[] = [
  {
    id: 'classic',
    name: 'Klassik Qo\'l',
    price: 0,
    description: 'Tabiiy yumshoq terili, oq yengli toza ko\'rinish',
    palmColor: '#ffd0b0',
    sleeveColor: '#ffffff',
    accentColor: '#f59e0b',
    glowColor: 'rgba(255, 208, 176, 0.4)',
    icon: '🖐️'
  },
  {
    id: 'cyber',
    name: 'Kiber Robot Qo\'l',
    price: 150,
    description: 'Neon ko\'k chiroqlar va titan temirli metall',
    palmColor: '#38bdf8',
    sleeveColor: '#0f172a',
    accentColor: '#00e5ff',
    glowColor: 'rgba(56, 189, 248, 0.5)',
    icon: '🦾'
  },
  {
    id: 'gold',
    name: 'Oltin Qirol Qo\'l',
    price: 300,
    description: 'Haqiqiy 24 karatli yaltiroq oltin qoplama',
    palmColor: '#fbbf24',
    sleeveColor: '#78350f',
    accentColor: '#f59e0b',
    glowColor: 'rgba(251, 191, 36, 0.6)',
    icon: '👑'
  },
  {
    id: 'lava',
    name: 'Olovli Magma Qo\'l',
    price: 500,
    description: 'Qaynoq vulqon va olovli cho\'g\'lar bilan yonadi',
    palmColor: '#ef4444',
    sleeveColor: '#1c1917',
    accentColor: '#f97316',
    glowColor: 'rgba(239, 68, 68, 0.6)',
    icon: '🔥'
  },
  {
    id: 'diamond',
    name: 'Olmos Billur Qo\'l',
    price: 800,
    description: 'Muzdek tiniq va porloq olmos kristallari',
    palmColor: '#a78bfa',
    sleeveColor: '#312e81',
    accentColor: '#c084fc',
    glowColor: 'rgba(167, 139, 250, 0.6)',
    icon: '💎'
  }
];

export function getHandSkin(id: HandSkinId): HandSkin {
  return HAND_SKINS.find(s => s.id === id) || HAND_SKINS[0];
}
