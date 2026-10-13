import { HandChoice, RoundOutcome, AIDifficulty, MatchState } from '../types';

export const CHOICES: HandChoice[] = ['rock', 'paper', 'scissors'];

export function determineRoundWinner(player: HandChoice, opponent: HandChoice): RoundOutcome {
  if (player === opponent) {
    return 'draw';
  }

  if (
    (player === 'rock' && opponent === 'scissors') ||
    (player === 'scissors' && opponent === 'paper') ||
    (player === 'paper' && opponent === 'rock')
  ) {
    return 'win';
  }

  return 'lose';
}

export function getCounterChoice(choice: HandChoice): HandChoice {
  switch (choice) {
    case 'rock':
      return 'paper';
    case 'paper':
      return 'scissors';
    case 'scissors':
      return 'rock';
  }
}

export function getLosingChoice(choice: HandChoice): HandChoice {
  switch (choice) {
    case 'rock':
      return 'scissors';
    case 'paper':
      return 'rock';
    case 'scissors':
      return 'paper';
  }
}

export function getAIMove(difficulty: AIDifficulty, playerHistory: HandChoice[]): HandChoice {
  // Pure random baseline
  const randomChoice = CHOICES[Math.floor(Math.random() * CHOICES.length)];

  if (difficulty === 'novice' || playerHistory.length === 0) {
    return randomChoice;
  }

  const lastPlayerMove = playerHistory[playerHistory.length - 1];

  if (difficulty === 'tactical') {
    // 60% chance to counter human heuristic: Humans often repeat what won or switch to what beat them
    if (Math.random() < 0.6) {
      return getCounterChoice(lastPlayerMove);
    }
    return randomChoice;
  }

  if (difficulty === 'grandmaster') {
    // Pattern analysis: frequency count of player moves
    const counts = { rock: 0, paper: 0, scissors: 0 };
    playerHistory.forEach(c => counts[c]++);
    const mostFrequent = (Object.keys(counts) as HandChoice[]).reduce((a, b) =>
      counts[a] >= counts[b] ? a : b
    );
    // 75% counter the predicted favorite
    if (Math.random() < 0.75) {
      return getCounterChoice(mostFrequent);
    }
  }

  return randomChoice;
}

export function isMatchOver(playerScore: number, opponentScore: number): boolean {
  return playerScore >= 2 || opponentScore >= 2;
}

export function getMatchWinner(playerScore: number, opponentScore: number): 'player' | 'opponent' | null {
  if (playerScore >= 2) return 'player';
  if (opponentScore >= 2) return 'opponent';
  return null;
}

export function createInitialMatchState(): MatchState {
  return {
    playerScore: 0,
    opponentScore: 0,
    roundsPlayed: 0,
    decisiveRounds: 0,
    history: [],
    winner: null
  };
}

export function getRoundOutcomeDescription(player: HandChoice, opponent: HandChoice): string {
  if (player === opponent) {
    return `Double ${player.toUpperCase()}! Impasse!`;
  }
  if (player === 'rock' && opponent === 'scissors') return 'Rock crushes Scissors!';
  if (player === 'scissors' && opponent === 'paper') return 'Scissors cuts Paper!';
  if (player === 'paper' && opponent === 'rock') return 'Paper covers Rock!';

  if (opponent === 'rock' && player === 'scissors') return 'Opponent Rock crushes Scissors!';
  if (opponent === 'scissors' && player === 'paper') return 'Opponent Scissors cuts Paper!';
  if (opponent === 'paper' && player === 'rock') return 'Opponent Paper covers Rock!';

  return '';
}
