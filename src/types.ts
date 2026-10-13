export type HandChoice = 'rock' | 'paper' | 'scissors';

export type GamePhase = 'ready' | 'countdown' | 'reveal' | 'roundResult' | 'matchResult';

export type RoundOutcome = 'win' | 'lose' | 'draw';

export type HandSkinId = 'classic' | 'cyber' | 'gold' | 'lava' | 'diamond';

export interface HandSkin {
  id: HandSkinId;
  name: string;
  price: number;
  description: string;
  palmColor: string;
  sleeveColor: string;
  accentColor: string;
  glowColor: string;
  icon: string;
}

export interface AvatarItem {
  id: string;
  name: string;
  price: number;
  icon: string;
  requiredWins?: number;
}

export interface UserProfile {
  name: string;
  coins: number;
  selectedAvatar: string;
  ownedAvatars: string[];
  selectedHandSkin: HandSkinId;
  ownedHandSkins: HandSkinId[];
  totalWins: number;
  totalMatches: number;
}

export interface RoundRecord {
  roundNumber: number;
  playerChoice: HandChoice;
  opponentChoice: HandChoice;
  outcome: RoundOutcome;
  isDecisive: boolean;
}

export interface MatchState {
  playerScore: number;
  opponentScore: number;
  roundsPlayed: number;
  decisiveRounds: number;
  history: RoundRecord[];
  winner: 'player' | 'opponent' | null;
}
