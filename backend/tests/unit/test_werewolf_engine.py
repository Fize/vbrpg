# -*- coding: utf-8 -*-
"""Unit tests for werewolf game engine."""

import pytest

from src.services.games.werewolf_engine import (
    DeathReason,
    NightSubPhase,
    PlayerState,
    WEREWOLF_10P_CONFIG,
    WerewolfEngine,
    WerewolfGameState,
    WerewolfPhase,
)


@pytest.fixture
def engine():
    """Create a werewolf engine instance."""
    return WerewolfEngine()


@pytest.fixture
def player_names():
    """Generate 10 player names."""
    return [f"Player_{i}" for i in range(1, 11)]


@pytest.fixture
def initialized_engine(engine, player_names):
    """Create an engine with initialized game state."""
    engine.initialize_game(
        room_code="TEST001",
        player_names=player_names,
    )
    return engine


@pytest.fixture
def started_engine(initialized_engine):
    """Create an engine with game started."""
    initialized_engine.start_game()
    return initialized_engine


class TestRoleAssignment:
    """Tests for role assignment."""

    def test_initialize_game_creates_10_players(self, engine, player_names):
        """Test that game initialization creates exactly 10 players."""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )

        assert len(state.players) == 10
        assert all(seat in state.players for seat in range(1, 11))

    def test_role_distribution_matches_config(self, engine, player_names):
        """Test that role distribution matches WEREWOLF_10P_CONFIG."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )

        role_counts = {}
        for player in engine.state.players.values():
            role_counts[player.role] = role_counts.get(player.role, 0) + 1

        assert role_counts == WEREWOLF_10P_CONFIG

    def test_user_gets_requested_role(self, engine, player_names):
        """Test that user gets the requested role at seat 1."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
            user_role="seer",
        )

        # User is always at seat 1
        assert engine.state.players[1].role == "seer"

    def test_user_role_werewolf(self, engine, player_names):
        """Test that user can request werewolf role."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
            user_role="werewolf",
        )

        assert engine.state.players[1].role == "werewolf"
        assert engine.state.players[1].team == "werewolf"

    def test_user_role_random_when_not_specified(self, engine, player_names):
        """Test that user gets random role when not specified."""
        roles_seen = set()
        for _ in range(50):  # Run multiple times to check randomness
            engine.initialize_game(
                room_code="TEST001",
                player_names=player_names,
            )
            roles_seen.add(engine.state.players[1].role)

        # Should see multiple different roles (randomness check)
        assert len(roles_seen) > 1

    def test_spectator_mode(self, engine, player_names):
        """Test spectator mode initialization."""
        state = engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
            is_spectator=True,
        )

        assert state.is_spectator_mode is True
        assert state.user_seat_number is None
        # All players should be AI
        assert all(p.is_ai for p in state.players.values())

    def test_player_mode_first_seat_not_ai(self, engine, player_names):
        """Test that in player mode, seat 1 is not AI."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
            is_spectator=False,
        )

        assert engine.state.players[1].is_ai is False
        assert engine.state.user_seat_number == 1
        # Other seats should be AI
        for seat in range(2, 11):
            assert engine.state.players[seat].is_ai is True

    def test_team_assignment(self, engine, player_names):
        """Test that teams are assigned correctly based on role."""
        engine.initialize_game(
            room_code="TEST001",
            player_names=player_names,
        )

        for player in engine.state.players.values():
            if player.role == "werewolf":
                assert player.team == "werewolf"
            else:
                assert player.team == "villager"

    def test_invalid_player_count(self, engine):
        """Test that invalid player count raises error."""
        with pytest.raises(ValueError) as exc_info:
            engine.initialize_game(
                room_code="TEST001",
                player_names=["P1", "P2", "P3"],  # Only 3 players
            )
        assert "exactly 10 players" in str(exc_info.value)


class TestPhaseTransitions:
    """Tests for phase transitions."""

    def test_initial_phase_is_waiting(self, initialized_engine):
        """Test that initial phase is waiting."""
        assert initialized_engine.state.phase == WerewolfPhase.WAITING

    def test_start_game_enters_night(self, initialized_engine):
        """Test that starting game enters night phase."""
        initialized_engine.start_game()

        assert initialized_engine.state.phase == WerewolfPhase.NIGHT
        assert initialized_engine.state.day_number == 1
        assert initialized_engine.state.sub_phase == NightSubPhase.WEREWOLF_ACTION.value

    def test_night_sub_phase_progression(self, started_engine):
        """Test night sub-phase progression."""
        # Initial: werewolf action
        assert started_engine.state.sub_phase == NightSubPhase.WEREWOLF_ACTION.value

        # Advance to seer
        next_phase = started_engine.advance_night_sub_phase()
        assert next_phase == NightSubPhase.SEER_ACTION.value
        assert started_engine.state.sub_phase == NightSubPhase.SEER_ACTION.value

        # Advance to witch
        next_phase = started_engine.advance_night_sub_phase()
        assert next_phase == NightSubPhase.WITCH_ACTION.value
        assert started_engine.state.sub_phase == NightSubPhase.WITCH_ACTION.value

        # Night ends
        next_phase = started_engine.advance_night_sub_phase()
        assert next_phase is None

    def test_start_day(self, started_engine):
        """Test transition to day phase."""
        started_engine.start_day()

        assert started_engine.state.phase == WerewolfPhase.DAY
        assert started_engine.state.sub_phase == "announcement"

    def test_start_discussion(self, started_engine):
        """Test start discussion phase."""
        started_engine.start_day()
        order = started_engine.start_discussion()

        assert started_engine.state.phase == WerewolfPhase.DISCUSSION
        assert len(order) == 10  # All players alive at start

    def test_start_vote(self, started_engine):
        """Test start vote phase."""
        started_engine.start_vote()

        assert started_engine.state.phase == WerewolfPhase.VOTE
        assert started_engine.state.current_votes == {}

    def test_transition_to_next_night(self, started_engine):
        """Test transition to next night."""
        initial_day = started_engine.state.day_number
        started_engine.transition_to_next_night()

        assert started_engine.state.day_number == initial_day + 1
        assert started_engine.state.phase == WerewolfPhase.NIGHT
        assert started_engine.state.sub_phase == NightSubPhase.WEREWOLF_ACTION.value


class TestNightActions:
    """Tests for night actions."""

    def test_set_werewolf_kill(self, started_engine):
        """Test setting werewolf kill target."""
        started_engine.set_werewolf_kill(3)

        assert started_engine.state.current_night_actions.werewolf_kill_target == 3

    def test_set_werewolf_empty_kill(self, started_engine):
        """Test setting empty werewolf kill."""
        started_engine.set_werewolf_kill(None)

        assert started_engine.state.current_night_actions.werewolf_kill_target is None

    def test_set_seer_check_werewolf(self, started_engine):
        """Test seer checking a werewolf."""
        # Find a werewolf seat
        werewolf_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "werewolf":
                werewolf_seat = seat
                break

        result = started_engine.set_seer_check(werewolf_seat)

        assert result is True
        assert started_engine.state.current_night_actions.seer_check_target == werewolf_seat

    def test_set_seer_check_villager(self, started_engine):
        """Test seer checking a non-werewolf."""
        # Find a non-werewolf seat
        villager_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role != "werewolf":
                villager_seat = seat
                break

        result = started_engine.set_seer_check(villager_seat)

        assert result is False

    def test_witch_save(self, started_engine):
        """Test witch using antidote."""
        assert started_engine.state.witch_has_antidote is True

        started_engine.set_witch_action(save=True)

        assert started_engine.state.current_night_actions.witch_save is True
        assert started_engine.state.witch_has_antidote is False

    def test_witch_poison(self, started_engine):
        """Test witch using poison."""
        assert started_engine.state.witch_has_poison is True

        started_engine.set_witch_action(poison_target=5)

        assert started_engine.state.current_night_actions.witch_poison_target == 5
        assert started_engine.state.witch_has_poison is False

    def test_witch_cannot_use_antidote_twice(self, started_engine):
        """Test witch cannot use antidote twice."""
        started_engine.set_witch_action(save=True)
        started_engine.state.current_night_actions = started_engine.state.current_night_actions.__class__()

        # Try to use again
        started_engine.set_witch_action(save=True)

        assert started_engine.state.current_night_actions.witch_save is False

    def test_process_night_werewolf_kill(self, started_engine):
        """Test processing night with werewolf kill."""
        target_seat = 3
        started_engine.set_werewolf_kill(target_seat)

        deaths = started_engine.process_night()

        assert len(deaths) == 1
        assert deaths[0]["seat_number"] == target_seat
        assert deaths[0]["reason"] == DeathReason.KILLED.value
        assert started_engine.state.players[target_seat].is_alive is False

    def test_process_night_witch_save(self, started_engine):
        """Test witch save prevents death."""
        target_seat = 3
        started_engine.set_werewolf_kill(target_seat)
        started_engine.set_witch_action(save=True)

        deaths = started_engine.process_night()

        assert len(deaths) == 0
        assert started_engine.state.players[target_seat].is_alive is True

    def test_process_night_witch_poison(self, started_engine):
        """Test witch poison causes death."""
        poison_target = 5
        started_engine.set_witch_action(poison_target=poison_target)

        deaths = started_engine.process_night()

        assert len(deaths) == 1
        assert deaths[0]["seat_number"] == poison_target
        assert deaths[0]["reason"] == DeathReason.POISONED.value

    def test_process_night_multiple_deaths(self, started_engine):
        """Test night with multiple deaths."""
        kill_target = 3
        poison_target = 5
        started_engine.set_werewolf_kill(kill_target)
        started_engine.set_witch_action(poison_target=poison_target)

        deaths = started_engine.process_night()

        assert len(deaths) == 2
        death_seats = {d["seat_number"] for d in deaths}
        assert death_seats == {kill_target, poison_target}


class TestVoting:
    """Tests for voting mechanics."""

    def test_cast_vote(self, started_engine):
        """Test casting a vote."""
        started_engine.start_vote()
        started_engine.cast_vote(voter_seat=1, target_seat=3)

        assert started_engine.state.current_votes[1] == 3

    def test_cast_abstain(self, started_engine):
        """Test abstaining from vote."""
        started_engine.start_vote()
        started_engine.cast_vote(voter_seat=1, target_seat=None)

        assert 1 not in started_engine.state.current_votes

    def test_tally_votes_clear_winner(self, started_engine):
        """Test tally with clear winner."""
        started_engine.start_vote()
        # 5 votes for player 3, 3 votes for player 5
        for voter in [1, 2, 4, 6, 7]:
            started_engine.cast_vote(voter, 3)
        for voter in [3, 5, 8]:
            started_engine.cast_vote(voter, 5)

        counts, eliminated, is_tie = started_engine.tally_votes()

        assert counts[3] == 5
        assert counts[5] == 3
        assert eliminated == 3
        assert is_tie is False

    def test_tally_votes_tie(self, started_engine):
        """Test tally with tie."""
        started_engine.start_vote()
        # 3 votes each for player 3 and 5
        for voter in [1, 2, 4]:
            started_engine.cast_vote(voter, 3)
        for voter in [3, 5, 6]:
            started_engine.cast_vote(voter, 5)

        counts, eliminated, is_tie = started_engine.tally_votes()

        assert counts[3] == 3
        assert counts[5] == 3
        assert eliminated is None
        assert is_tie is True

    def test_tally_votes_all_abstain(self, started_engine):
        """Test tally when all abstain."""
        started_engine.start_vote()
        # No votes cast

        counts, eliminated, is_tie = started_engine.tally_votes()

        assert counts == {}
        assert eliminated is None
        assert is_tie is True

    def test_execute_vote_result(self, started_engine):
        """Test executing vote result."""
        target_seat = 3
        death_info = started_engine.execute_vote_result(target_seat)

        assert death_info is not None
        assert death_info["seat_number"] == target_seat
        assert death_info["reason"] == DeathReason.VOTED.value
        assert started_engine.state.players[target_seat].is_alive is False


class TestHunterShoot:
    """Tests for hunter shooting mechanics."""

    def test_hunter_can_shoot_when_killed(self, started_engine):
        """Test hunter can shoot when killed by werewolves."""
        # Find hunter seat
        hunter_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "hunter":
                hunter_seat = seat
                break

        can_shoot = started_engine.can_hunter_shoot(hunter_seat, DeathReason.KILLED)
        assert can_shoot is True

    def test_hunter_can_shoot_when_voted(self, started_engine):
        """Test hunter can shoot when voted out."""
        hunter_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "hunter":
                hunter_seat = seat
                break

        can_shoot = started_engine.can_hunter_shoot(hunter_seat, DeathReason.VOTED)
        assert can_shoot is True

    def test_hunter_cannot_shoot_when_poisoned(self, started_engine):
        """Test hunter cannot shoot when poisoned."""
        hunter_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "hunter":
                hunter_seat = seat
                break

        can_shoot = started_engine.can_hunter_shoot(hunter_seat, DeathReason.POISONED)
        assert can_shoot is False

    def test_non_hunter_cannot_shoot(self, started_engine):
        """Test non-hunter cannot shoot."""
        # Find non-hunter seat
        non_hunter_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role != "hunter":
                non_hunter_seat = seat
                break

        can_shoot = started_engine.can_hunter_shoot(non_hunter_seat, DeathReason.KILLED)
        assert can_shoot is False

    def test_hunter_shoot_execution(self, started_engine):
        """Test hunter shoot kills target."""
        hunter_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "hunter":
                hunter_seat = seat
                break

        target_seat = 5 if hunter_seat != 5 else 6
        death_info = started_engine.hunter_shoot(hunter_seat, target_seat)

        assert death_info is not None
        assert death_info["seat_number"] == target_seat
        assert death_info["reason"] == DeathReason.SHOT.value
        assert death_info["hunter_seat"] == hunter_seat
        assert started_engine.state.players[target_seat].is_alive is False


class TestWinCondition:
    """Tests for win condition checking."""

    def test_no_winner_at_start(self, started_engine):
        """Test no winner at game start."""
        winner = started_engine.check_win_condition()
        assert winner is None

    def test_werewolf_wins_when_equal_numbers(self, started_engine):
        """Test werewolves win when numbers are equal."""
        # Kill enough villagers to make numbers equal
        # 3 werewolves, need 3 or fewer good players
        villagers_to_kill = 4  # Leave 3 good vs 3 wolves

        killed = 0
        for seat, player in started_engine.state.players.items():
            if player.role != "werewolf" and killed < villagers_to_kill:
                player.is_alive = False
                killed += 1

        winner = started_engine.check_win_condition()
        assert winner == "werewolf"
        assert started_engine.state.phase == WerewolfPhase.ENDED

    def test_werewolf_wins_when_majority(self, started_engine):
        """Test werewolves win when they have majority."""
        # Kill more villagers
        killed = 0
        for seat, player in started_engine.state.players.items():
            if player.role != "werewolf" and killed < 5:
                player.is_alive = False
                killed += 1

        winner = started_engine.check_win_condition()
        assert winner == "werewolf"

    def test_villager_wins_when_all_wolves_dead(self, started_engine):
        """Test villagers win when all werewolves dead."""
        for player in started_engine.state.players.values():
            if player.role == "werewolf":
                player.is_alive = False

        winner = started_engine.check_win_condition()
        assert winner == "villager"
        assert started_engine.state.phase == WerewolfPhase.ENDED

    def test_game_continues_normally(self, started_engine):
        """Test game continues when neither side wins."""
        # Kill one villager (3 wolves vs 6 good)
        for seat, player in started_engine.state.players.items():
            if player.role == "villager":
                player.is_alive = False
                break

        winner = started_engine.check_win_condition()
        assert winner is None
        assert started_engine.state.phase != WerewolfPhase.ENDED


class TestHelperMethods:
    """Tests for helper methods."""

    def test_get_alive_players(self, started_engine):
        """Test getting alive players."""
        alive = started_engine.get_alive_players()
        assert len(alive) == 10

        # Kill one
        started_engine.state.players[3].is_alive = False
        alive = started_engine.get_alive_players()
        assert len(alive) == 9

    def test_get_alive_player_by_seat(self, started_engine):
        """Test getting alive player by seat."""
        player = started_engine.get_alive_player_by_seat(3)
        assert player is not None
        assert player.seat_number == 3

        # Kill and check again
        started_engine.state.players[3].is_alive = False
        player = started_engine.get_alive_player_by_seat(3)
        assert player is None

    def test_get_player_by_seat(self, started_engine):
        """Test getting player by seat (dead or alive)."""
        player = started_engine.get_player_by_seat(3)
        assert player is not None

        started_engine.state.players[3].is_alive = False
        player = started_engine.get_player_by_seat(3)
        assert player is not None  # Still returns dead player

    def test_get_werewolf_teammates(self, started_engine):
        """Test getting werewolf teammates."""
        # Find a werewolf
        wolf_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "werewolf":
                wolf_seat = seat
                break

        teammates = started_engine.get_werewolf_teammates(wolf_seat)
        assert len(teammates) == 2  # 3 wolves total, minus self
        assert all(t.role == "werewolf" for t in teammates)
        assert all(t.seat_number != wolf_seat for t in teammates)

    def test_get_werewolf_teammates_non_wolf(self, started_engine):
        """Test getting teammates for non-werewolf returns empty."""
        # Find a non-werewolf
        non_wolf_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role != "werewolf":
                non_wolf_seat = seat
                break

        teammates = started_engine.get_werewolf_teammates(non_wolf_seat)
        assert teammates == []

    def test_count_teams(self, started_engine):
        """Test counting teams."""
        wolf_count, good_count = started_engine.count_teams()
        assert wolf_count == 3
        assert good_count == 7

        # Kill a werewolf
        for player in started_engine.state.players.values():
            if player.role == "werewolf":
                player.is_alive = False
                break

        wolf_count, good_count = started_engine.count_teams()
        assert wolf_count == 2
        assert good_count == 7


class TestSerialization:
    """Tests for state serialization."""

    def test_get_public_state(self, started_engine):
        """Test getting public state."""
        state = started_engine.get_public_state()

        assert state["room_code"] == "TEST001"
        assert state["day_number"] == 1
        assert state["phase"] == WerewolfPhase.NIGHT.value
        assert len(state["alive_players"]) == 10
        assert state["dead_players"] == []
        assert state["winner"] is None

    def test_get_public_state_hides_roles(self, started_engine):
        """Test that public state hides roles during game."""
        state = started_engine.get_public_state()

        for player in state["alive_players"]:
            assert "role" not in player

    def test_get_public_state_shows_roles_when_ended(self, started_engine):
        """Test that public state shows roles when game ended."""
        # End the game
        started_engine.state.phase = WerewolfPhase.ENDED
        started_engine.state.players[3].is_alive = False

        state = started_engine.get_public_state()

        # Dead players show role when game ended
        for dead in state["dead_players"]:
            assert dead["role"] is not None

    def test_get_player_state(self, started_engine):
        """Test getting player state."""
        state = started_engine.get_player_state(1)

        assert state is not None
        assert state["seat_number"] == 1
        assert "role" in state
        assert "team" in state

    def test_get_player_state_werewolf_has_teammates(self, started_engine):
        """Test werewolf player state includes teammates."""
        # Find a werewolf
        wolf_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "werewolf":
                wolf_seat = seat
                break

        state = started_engine.get_player_state(wolf_seat)

        assert "teammates" in state
        assert len(state["teammates"]) == 2

    def test_get_player_state_witch_has_potions(self, started_engine):
        """Test witch player state includes potion status."""
        # Find witch
        witch_seat = None
        for seat, player in started_engine.state.players.items():
            if player.role == "witch":
                witch_seat = seat
                break

        state = started_engine.get_player_state(witch_seat)

        assert "has_antidote" in state
        assert "has_poison" in state
        assert state["has_antidote"] is True
        assert state["has_poison"] is True


class TestSpeechHistory:
    """Tests for speech recording."""

    def test_add_speech(self, started_engine):
        """Test adding a speech."""
        started_engine.add_speech(seat=3, content="我是好人")

        assert len(started_engine.state.speech_history) == 1
        assert started_engine.state.speech_history[0]["seat_number"] == 3
        assert started_engine.state.speech_history[0]["content"] == "我是好人"
