export type HandChoice = 'rock' | 'paper' | 'scissors';

export type GamePhase = 'ready' | 'countdown' | 'reveal' | 'roundResult' | 'matchResult';

export type RoundOutcome = 'win' | 'lose' | 'draw';

export type AIDifficulty = 'novice' | 'tactical' | 'grandmaster';

export type GameMode = 'ai' | 'online';

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
