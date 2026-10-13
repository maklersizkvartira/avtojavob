import React, { useState, useEffect, useCallback } from 'react';
import {
  HandChoice,
  RoundOutcome,
  UserProfile,
  MatchState
} from './types';
import {
  determineRoundWinner,
  getAIMove,
  createInitialMatchState
} from './utils/gameLogic';
import { getHandSkin } from './utils/shopData';
import { sound } from './utils/audio';
import { TopBar } from './components/TopBar';
import { ArenaCards } from './components/ArenaCards';
import { ChoiceButtons } from './components/ChoiceButtons';
import { ResultBanner } from './components/ResultBanner';
import { MatchWinnerModal } from './components/MatchWinnerModal';
import { WelcomeModal } from './components/WelcomeModal';
import { ShopModal } from './components/ShopModal';
import { ProfileModal } from './components/ProfileModal';

const DEFAULT_PROFILE: UserProfile = {
  name: 'O\'yinchi',
  coins: 200,
  selectedAvatar: 'avatar_boy',
  ownedAvatars: ['avatar_boy'],
  selectedHandSkin: 'classic',
  ownedHandSkins: ['classic'],
  totalWins: 0,
  totalMatches: 0
};

export const App: React.FC = () => {
  // User Profile & Coins
  const [profile, setProfile] = useState<UserProfile>(() => {
    const saved = localStorage.getItem('hog_user_profile');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // fallback
      }
    }
    return DEFAULT_PROFILE;
  });

  const [showWelcome, setShowWelcome] = useState<boolean>(() => {
    return !localStorage.getItem('hog_user_profile');
  });

  // UI Modals
  const [showShop, setShowShop] = useState<boolean>(false);
  const [showProfile, setShowProfile] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(sound.isMuted());

  // Game Match State
  const [matchState, setMatchState] = useState<MatchState>(createInitialMatchState());
  const [playerChoice, setPlayerChoice] = useState<HandChoice>('rock');
  const [opponentChoice, setOpponentChoice] = useState<HandChoice>('scissors');
  const [roundOutcome, setRoundOutcome] = useState<RoundOutcome | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isShaking, setIsShaking] = useState<boolean>(false);
  const [earnedCoins, setEarnedCoins] = useState<number>(0);

  // Sync profile to localStorage & server
  const updateProfile = useCallback((updated: UserProfile) => {
    setProfile(updated);
    localStorage.setItem('hog_user_profile', JSON.stringify(updated));
  }, []);

  // Welcome modal completion
  const handleWelcomeComplete = (name: string, avatar: string) => {
    const newProfile: UserProfile = {
      ...DEFAULT_PROFILE,
      name,
      selectedAvatar: avatar,
      ownedAvatars: [avatar]
    };
    updateProfile(newProfile);
    setShowWelcome(false);
  };

  // Sound toggle
  const handleToggleSound = () => {
    const muted = sound.toggleMute();
    setIsMuted(muted);
  };

  // Reset match
  const handleResetMatch = useCallback(() => {
    setMatchState(createInitialMatchState());
    setRoundOutcome(null);
    setIsPlaying(false);
    setIsShaking(false);
    sound.playTap();
  }, []);

  // Choice selector
  const handleSelectChoice = (choice: HandChoice) => {
    if (isPlaying) return;
    sound.playTap();
    setPlayerChoice(choice);
    // Clear last banner when a new weapon is chosen
    setRoundOutcome(null);
  };

  // PLAY ROUND ACTION (Raundni o'yna)
  const handlePlayRound = () => {
    if (isPlaying || matchState.winner) return;

    setIsPlaying(true);
    setIsShaking(true);
    setRoundOutcome(null);
    sound.playTap();

    // Rhythmic countdown sounds
    sound.playCountdownTick(3);
    setTimeout(() => sound.playCountdownTick(2), 350);
    setTimeout(() => sound.playCountdownTick(1), 700);

    // AI selects independent move
    const playerHistory = matchState.history.map(h => h.playerChoice);
    const botChoice = getAIMove('tactical', playerHistory);

    // Reveal after 1 second of shaking
    setTimeout(() => {
      setIsShaking(false);
      setOpponentChoice(botChoice);
      sound.playImpact();

      const outcome = determineRoundWinner(playerChoice, botChoice);
      setRoundOutcome(outcome);

      // Score and coins calculation
      let addedCoins = 0;
      let newPScore = matchState.playerScore;
      let newOpScore = matchState.opponentScore;

      if (outcome === 'win') {
        newPScore += 1;
        addedCoins += 50; // +50 tanga for round win
        setTimeout(() => {
          sound.playWin();
          sound.playCoin();
        }, 200);
      } else if (outcome === 'lose') {
        newOpScore += 1;
        addedCoins += 10; // +10 consolation coins
        setTimeout(() => sound.playLose(), 200);
      } else {
        setTimeout(() => sound.playDraw(), 200);
      }

      // Check if match won (best of 3: first to 2 points)
      let matchWinner: 'player' | 'opponent' | null = null;
      let matchBonus = 0;

      if (newPScore >= 2) {
        matchWinner = 'player';
        matchBonus = 150; // +150 bonus coins for match win!
        addedCoins += matchBonus;
      } else if (newOpScore >= 2) {
        matchWinner = 'opponent';
      }

      setEarnedCoins(matchBonus || addedCoins);

      // Update User Profile Coins & Stats
      const updatedProfile: UserProfile = {
        ...profile,
        coins: profile.coins + addedCoins,
        totalWins: matchWinner === 'player' ? profile.totalWins + 1 : profile.totalWins,
        totalMatches: matchWinner ? profile.totalMatches + 1 : profile.totalMatches
      };
      updateProfile(updatedProfile);

      // Update Match State
      const updatedMatch: MatchState = {
        playerScore: newPScore,
        opponentScore: newOpScore,
        roundsPlayed: matchState.roundsPlayed + 1,
        decisiveRounds: newPScore + newOpScore,
        history: [
          ...matchState.history,
          {
            roundNumber: matchState.roundsPlayed + 1,
            playerChoice,
            opponentChoice: botChoice,
            outcome,
            isDecisive: outcome !== 'draw'
          }
        ],
        winner: matchWinner
      };
      setMatchState(updatedMatch);
      setIsPlaying(false);
    }, 1050);
  };

  // Next round advance
  const handleNextRound = () => {
    setRoundOutcome(null);
    sound.playTap();
  };

  const currentRound = matchState.roundsPlayed + 1;
  const playerHandSkin = getHandSkin(profile.selectedHandSkin);
  const matchInProgress = matchState.playerScore > 0 || matchState.opponentScore > 0;

  return (
    <div className="relative min-h-screen w-full bg-[#0d1117] text-slate-100 flex flex-col justify-between overflow-x-hidden font-['Outfit',sans-serif]">
      {/* Subtle soft backdrop glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-60 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Header */}
      <TopBar
        profile={profile}
        isMuted={isMuted}
        onToggleSound={handleToggleSound}
        onResetMatch={handleResetMatch}
        onOpenProfile={() => setShowProfile(true)}
        onOpenShop={() => setShowShop(true)}
        matchInProgress={matchInProgress}
      />

      {/* Main Game Screen */}
      <main className="flex-1 flex flex-col justify-center items-center w-full max-w-xl mx-auto px-2 relative z-10">
        {/* Arena Cards: Sen vs Kompyuter with 3D stylized hands */}
        <ArenaCards
          playerChoice={playerChoice}
          opponentChoice={opponentChoice}
          playerScore={matchState.playerScore}
          opponentScore={matchState.opponentScore}
          currentRound={currentRound}
          playerName={profile.name}
          playerHandSkin={playerHandSkin}
          isShaking={isShaking}
        />

        {/* Round Outcome Banner */}
        <ResultBanner
          outcome={roundOutcome}
          playerChoice={playerChoice}
          opponentChoice={opponentChoice}
          onNextRound={handleNextRound}
          isMatchOver={Boolean(matchState.winner)}
        />

        {/* Choice Buttons & Raundni o'yna Button */}
        <ChoiceButtons
          selectedChoice={playerChoice}
          onSelectChoice={handleSelectChoice}
          onPlayRound={handlePlayRound}
          isPlaying={isPlaying}
        />
      </main>

      {/* Footer */}
      <footer className="w-full text-center py-2 text-[11px] text-slate-500 font-medium select-none">
        <span>Tosh • Qog'oz • Qaychi — 3 tadan 2 ta g'alaba (Best of 3)</span>
      </footer>

      {/* Welcome / Onboarding Modal (Name entry) */}
      <WelcomeModal
        isOpen={showWelcome}
        onComplete={handleWelcomeComplete}
      />

      {/* Shop Modal (Avatars & Hand Skins) */}
      <ShopModal
        isOpen={showShop}
        onClose={() => setShowShop(false)}
        profile={profile}
        onUpdateProfile={updateProfile}
      />

      {/* Profile Modal */}
      <ProfileModal
        isOpen={showProfile}
        onClose={() => setShowProfile(false)}
        profile={profile}
        onUpdateProfile={updateProfile}
        onOpenShop={() => setShowShop(true)}
      />

      {/* Match Winner Modal */}
      {matchState.winner && (
        <MatchWinnerModal
          winner={matchState.winner}
          matchState={matchState}
          onPlayAgain={handleResetMatch}
          earnedCoins={earnedCoins}
        />
      )}
    </div>
  );
};
export default App;
