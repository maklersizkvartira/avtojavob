// Comprehensive test suite for Hands of Glory game logic

import { determineRoundWinner, isMatchOver, getMatchWinner, createInitialMatchState } from '../src/utils/gameLogic.js';

let passed = 0;
let total = 0;

function assert(condition, message) {
  total++;
  if (condition) {
    passed++;
    console.log(`  ✓ PASS: ${message}`);
  } else {
    console.error(`  ✗ FAIL: ${message}`);
    process.exitCode = 1;
  }
}

console.log('\n--- 1. Testing RPS Matchup Rules ---');
// Rock vs all
assert(determineRoundWinner('rock', 'rock') === 'draw', 'Player ROCK vs Computer ROCK = DRAW');
assert(determineRoundWinner('rock', 'paper') === 'lose', 'Player ROCK vs Computer PAPER = PLAYER LOSES');
assert(determineRoundWinner('rock', 'scissors') === 'win', 'Player ROCK vs Computer SCISSORS = PLAYER WINS');

// Paper vs all
assert(determineRoundWinner('paper', 'rock') === 'win', 'Player PAPER vs Computer ROCK = PLAYER WINS');
assert(determineRoundWinner('paper', 'paper') === 'draw', 'Player PAPER vs Computer PAPER = DRAW');
assert(determineRoundWinner('paper', 'scissors') === 'lose', 'Player PAPER vs Computer SCISSORS = PLAYER LOSES');

// Scissors vs all
assert(determineRoundWinner('scissors', 'rock') === 'lose', 'Player SCISSORS vs Computer ROCK = PLAYER LOSES');
assert(determineRoundWinner('scissors', 'paper') === 'win', 'Player SCISSORS vs Computer PAPER = PLAYER WINS');
assert(determineRoundWinner('scissors', 'scissors') === 'draw', 'Player SCISSORS vs Computer SCISSORS = DRAW');

console.log('\n--- 2. Testing Best of 3 Match Logic ---');
// Player wins 2-0: ends immediately
assert(isMatchOver(2, 0) === true, 'Player wins first 2 rounds: match ends immediately');
assert(getMatchWinner(2, 0) === 'player', 'Player declared match winner at 2-0');

// Computer wins 2-0: ends immediately
assert(isMatchOver(0, 2) === true, 'Computer wins first 2 rounds: match ends immediately');
assert(getMatchWinner(0, 2) === 'opponent', 'Computer declared match winner at 0-2');

// Score 1-1: third round needed
assert(isMatchOver(1, 1) === false, 'Score 1-1: match continues to round 3');
assert(getMatchWinner(1, 1) === null, 'Score 1-1: no winner yet');

// Score 2-1: ends
assert(isMatchOver(2, 1) === true, 'Score 2-1: match ends with player victory');
assert(getMatchWinner(2, 1) === 'player', 'Player is winner at 2-1');

// Score 1-2: ends
assert(isMatchOver(1, 2) === true, 'Score 1-2: match ends with computer victory');
assert(getMatchWinner(1, 2) === 'opponent', 'Computer is winner at 1-2');

console.log('\n--- 3. Testing Draw Handling & State Reset ---');
const initial = createInitialMatchState();
assert(initial.playerScore === 0 && initial.opponentScore === 0, 'Initial score is 0-0');
assert(initial.winner === null, 'Initial winner is null');
assert(initial.roundsPlayed === 0, 'Initial roundsPlayed is 0');

console.log(`\n========================================`);
console.log(`Test Results: ${passed}/${total} passed!`);
console.log(`========================================\n`);
