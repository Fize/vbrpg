# -*- coding: utf-8 -*-
"""Integration tests for werewolf WebSocket event handlers."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


@pytest.fixture
def mock_sio():
    """Create a mock Socket.IO server."""
    sio = MagicMock()
    sio.emit = AsyncMock()
    sio.enter_room = AsyncMock()
    sio.leave_room = AsyncMock()
    return sio


@pytest.fixture
def sample_room_code():
    """Sample room code."""
    return "WEREWOLF001"


@pytest.fixture
def sample_alive_players():
    """Sample alive players list."""
    return [
        {"seat_number": i, "display_name": f"Player_{i}"}
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_dead_players():
    """Sample dead players list."""
    return [
        {
            "seat_number": 3,
            "display_name": "Player_3",
            "death_reason": "killed",
            "death_day": 1,
        }
    ]


@pytest.mark.asyncio
class TestHostAnnouncementEvents:
    """Tests for host announcement WebSocket events."""

    async def test_broadcast_host_announcement(self, mock_sio, sample_room_code):
        """Test broadcasting host announcement to room."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_host_announcement

            await broadcast_host_announcement(
                room_code=sample_room_code,
                announcement_type="game_start",
                content="游戏开始！天黑请闭眼。",
                metadata={"day_number": 1},
            )

            mock_sio.emit.assert_called_once_with(
                "werewolf:host_announcement",
                {
                    "type": "game_start",
                    "content": "游戏开始！天黑请闭眼。",
                    "metadata": {"day_number": 1},
                },
                room=sample_room_code,
            )

    async def test_broadcast_host_announcement_no_metadata(self, mock_sio, sample_room_code):
        """Test broadcasting announcement without metadata."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_host_announcement

            await broadcast_host_announcement(
                room_code=sample_room_code,
                announcement_type="night_start",
                content="天黑请闭眼",
            )

            call_args = mock_sio.emit.call_args
            assert call_args[0][1]["metadata"] == {}

    async def test_stream_host_announcement(self, mock_sio, sample_room_code):
        """Test streaming host announcement."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import stream_host_announcement

            async def content_generator():
                for char in "测试":
                    yield char

            await stream_host_announcement(
                room_code=sample_room_code,
                announcement_type="dawn",
                content_stream=content_generator(),
                metadata={"deaths": []},
            )

            # Should have start, chunk(s), and end events
            assert mock_sio.emit.call_count >= 3

            # Check start event
            start_call = mock_sio.emit.call_args_list[0]
            assert start_call[0][0] == "werewolf:host_announcement_start"
            assert start_call[0][1]["type"] == "dawn"

            # Check end event (last call)
            end_call = mock_sio.emit.call_args_list[-1]
            assert end_call[0][0] == "werewolf:host_announcement_end"
            assert end_call[0][1]["content"] == "测试"


@pytest.mark.asyncio
class TestGameStateEvents:
    """Tests for game state WebSocket events."""

    async def test_broadcast_game_state_update(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test broadcasting game state update."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_game_state_update

            await broadcast_game_state_update(
                room_code=sample_room_code,
                phase="night",
                day_number=1,
                alive_players=sample_alive_players,
                dead_players=[],
            )

            mock_sio.emit.assert_called_once_with(
                "werewolf:game_state",
                {
                    "phase": "night",
                    "day_number": 1,
                    "alive_players": sample_alive_players,
                    "dead_players": [],
                    "current_speaker": None,
                },
                room=sample_room_code,
            )

    async def test_broadcast_game_state_with_speaker(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test broadcasting game state with current speaker."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_game_state_update

            current_speaker = {"seat_number": 1, "display_name": "Player_1"}

            await broadcast_game_state_update(
                room_code=sample_room_code,
                phase="discussion",
                day_number=2,
                alive_players=sample_alive_players,
                dead_players=[],
                current_speaker=current_speaker,
            )

            call_args = mock_sio.emit.call_args[0][1]
            assert call_args["current_speaker"] == current_speaker

    async def test_broadcast_phase_change(self, mock_sio, sample_room_code):
        """Test broadcasting phase change event."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_phase_change

            await broadcast_phase_change(
                room_code=sample_room_code,
                from_phase="night",
                to_phase="day",
                day_number=1,
            )

            mock_sio.emit.assert_called_once_with(
                "werewolf:phase_change",
                {
                    "from_phase": "night",
                    "to_phase": "day",
                    "day_number": 1,
                },
                room=sample_room_code,
            )


@pytest.mark.asyncio
class TestNightActionEvents:
    """Tests for night action WebSocket events."""

    async def test_notify_werewolf_turn(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test notifying werewolf players of their turn."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_werewolf_turn

            mock_get_sid.return_value = "sid_werewolf_1"

            await notify_werewolf_turn(
                room_code=sample_room_code,
                werewolf_player_ids=["werewolf_1"],
                alive_targets=sample_alive_players,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:your_turn"
            assert call_args[0][1]["role"] == "werewolf"
            assert call_args[0][1]["action"] == "kill"

    async def test_notify_seer_turn(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test notifying seer of their turn."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_seer_turn

            mock_get_sid.return_value = "sid_seer"

            await notify_seer_turn(
                room_code=sample_room_code,
                seer_player_id="seer_1",
                alive_targets=sample_alive_players,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:your_turn"
            assert call_args[0][1]["role"] == "seer"
            assert call_args[0][1]["action"] == "check"

    async def test_notify_seer_result(self, mock_sio, sample_room_code):
        """Test notifying seer of check result."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_seer_result

            mock_get_sid.return_value = "sid_seer"

            await notify_seer_result(
                room_code=sample_room_code,
                seer_player_id="seer_1",
                target_seat=3,
                target_name="Player_3",
                is_werewolf=True,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:seer_result"
            assert call_args[0][1]["is_werewolf"] is True
            assert "狼人" in call_args[0][1]["message"]

    async def test_notify_seer_result_not_werewolf(self, mock_sio, sample_room_code):
        """Test notifying seer of good player check result."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_seer_result

            mock_get_sid.return_value = "sid_seer"

            await notify_seer_result(
                room_code=sample_room_code,
                seer_player_id="seer_1",
                target_seat=5,
                target_name="Player_5",
                is_werewolf=False,
            )

            call_args = mock_sio.emit.call_args
            assert call_args[0][1]["is_werewolf"] is False
            assert "好人" in call_args[0][1]["message"]

    async def test_notify_witch_turn(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test notifying witch of their turn."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_witch_turn

            mock_get_sid.return_value = "sid_witch"
            killed_player = {"seat_number": 3, "display_name": "Player_3"}

            await notify_witch_turn(
                room_code=sample_room_code,
                witch_player_id="witch_1",
                killed_player=killed_player,
                has_antidote=True,
                has_poison=True,
                can_self_save=False,
                alive_targets=sample_alive_players,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:your_turn"
            assert call_args[0][1]["role"] == "witch"
            assert call_args[0][1]["has_antidote"] is True
            assert call_args[0][1]["has_poison"] is True
            assert call_args[0][1]["killed_player"] == killed_player

    async def test_notify_hunter_shoot(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test notifying hunter they can shoot."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_hunter_shoot

            mock_get_sid.return_value = "sid_hunter"

            await notify_hunter_shoot(
                room_code=sample_room_code,
                hunter_player_id="hunter_1",
                alive_targets=sample_alive_players,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:hunter_shoot"
            assert call_args[0][1]["role"] == "hunter"
            assert call_args[0][1]["action"] == "shoot"


@pytest.mark.asyncio
class TestSpeechEvents:
    """Tests for AI speech streaming events."""

    async def test_stream_ai_speech(self, mock_sio, sample_room_code):
        """Test streaming AI player speech."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import stream_ai_speech

            async def speech_generator():
                for word in ["大家好", "我是", "村民"]:
                    yield word

            await stream_ai_speech(
                room_code=sample_room_code,
                speaker_seat=3,
                speaker_name="Player_3",
                speech_stream=speech_generator(),
            )

            # Should have start, chunks, and end events
            assert mock_sio.emit.call_count >= 3

            # Check start event
            start_call = mock_sio.emit.call_args_list[0]
            assert start_call[0][0] == "werewolf:speech_start"
            assert start_call[0][1]["speaker_seat"] == 3
            assert start_call[0][1]["speaker_name"] == "Player_3"

            # Check end event
            end_call = mock_sio.emit.call_args_list[-1]
            assert end_call[0][0] == "werewolf:speech_end"

    async def test_stream_ai_speech_chunks(self, mock_sio, sample_room_code):
        """Test that speech chunks are emitted correctly."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import stream_ai_speech

            chunks = ["第一", "第二", "第三"]

            async def speech_generator():
                for chunk in chunks:
                    yield chunk

            await stream_ai_speech(
                room_code=sample_room_code,
                speaker_seat=5,
                speaker_name="Player_5",
                speech_stream=speech_generator(),
            )

            # Extract chunk events (middle calls)
            all_calls = mock_sio.emit.call_args_list
            chunk_calls = [c for c in all_calls if c[0][0] == "werewolf:speech_chunk"]

            assert len(chunk_calls) == 3
            for i, call in enumerate(chunk_calls):
                assert call[0][1]["chunk"] == chunks[i]


@pytest.mark.asyncio
class TestVoteEvents:
    """Tests for voting WebSocket events."""

    async def test_broadcast_vote_update(self, mock_sio, sample_room_code):
        """Test broadcasting vote update."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_vote_update

            await broadcast_vote_update(
                room_code=sample_room_code,
                voter_seat=1,
                voter_name="Player_1",
                target_seat=3,
                target_name="Player_3",
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:vote_update"
            assert call_args[0][1]["voter_seat"] == 1
            assert call_args[0][1]["target_seat"] == 3
            assert call_args[0][1]["is_abstain"] is False

    async def test_broadcast_vote_update_abstain(self, mock_sio, sample_room_code):
        """Test broadcasting abstain vote."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_vote_update

            await broadcast_vote_update(
                room_code=sample_room_code,
                voter_seat=2,
                voter_name="Player_2",
                target_seat=None,
                target_name=None,
            )

            call_args = mock_sio.emit.call_args
            assert call_args[0][1]["is_abstain"] is True

    async def test_broadcast_vote_result(self, mock_sio, sample_room_code):
        """Test broadcasting vote result."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_vote_result

            vote_counts = {3: 4, 5: 2, None: 1}

            await broadcast_vote_result(
                room_code=sample_room_code,
                vote_counts=vote_counts,
                eliminated_seat=3,
                eliminated_name="Player_3",
                is_tie=False,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:vote_result"
            assert call_args[0][1]["eliminated_seat"] == 3
            assert call_args[0][1]["is_tie"] is False

    async def test_broadcast_vote_result_tie(self, mock_sio, sample_room_code):
        """Test broadcasting tie vote result."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_vote_result

            vote_counts = {3: 3, 5: 3}

            await broadcast_vote_result(
                room_code=sample_room_code,
                vote_counts=vote_counts,
                eliminated_seat=None,
                eliminated_name=None,
                is_tie=True,
            )

            call_args = mock_sio.emit.call_args
            assert call_args[0][1]["eliminated_seat"] is None
            assert call_args[0][1]["is_tie"] is True


@pytest.mark.asyncio
class TestGameOverEvent:
    """Tests for game over WebSocket event."""

    async def test_broadcast_game_over_werewolf_wins(self, mock_sio, sample_room_code):
        """Test broadcasting werewolf victory."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_game_over

            winning_players = [
                {"seat_number": 1, "name": "P1", "role": "werewolf"},
                {"seat_number": 3, "name": "P3", "role": "werewolf"},
            ]
            all_players = [
                {"seat_number": 1, "name": "P1", "role": "werewolf"},
                {"seat_number": 2, "name": "P2", "role": "villager"},
            ]

            await broadcast_game_over(
                room_code=sample_room_code,
                winner="werewolf",
                winning_players=winning_players,
                all_players=all_players,
            )

            mock_sio.emit.assert_called_once()
            call_args = mock_sio.emit.call_args
            assert call_args[0][0] == "werewolf:game_over"
            assert call_args[0][1]["winner"] == "werewolf"
            assert "狼人" in call_args[0][1]["winner_name"]

    async def test_broadcast_game_over_villager_wins(self, mock_sio, sample_room_code):
        """Test broadcasting villager victory."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio):
            from src.websocket.werewolf_handlers import broadcast_game_over

            await broadcast_game_over(
                room_code=sample_room_code,
                winner="villager",
                winning_players=[],
                all_players=[],
            )

            call_args = mock_sio.emit.call_args
            assert call_args[0][1]["winner"] == "villager"
            assert "好人" in call_args[0][1]["winner_name"]


@pytest.mark.asyncio
class TestHelperFunctions:
    """Tests for helper functions in werewolf handlers."""

    async def test_get_sid_by_player_id_found(self):
        """Test getting SID for existing player."""
        # Need to patch the actual user_sessions dict used by the function
        with patch.dict(
            'src.websocket.werewolf_handlers.user_sessions',
            {"sid_123": "player_1"},
            clear=True
        ):
            from src.websocket.werewolf_handlers import _get_sid_by_player_id

            result = _get_sid_by_player_id("player_1")
            assert result == "sid_123"

    async def test_get_sid_by_player_id_not_found(self):
        """Test getting SID for non-existent player."""
        with patch.dict(
            'src.websocket.werewolf_handlers.user_sessions',
            {},
            clear=True
        ):
            from src.websocket.werewolf_handlers import _get_sid_by_player_id

            result = _get_sid_by_player_id("player_unknown")
            assert result is None

    async def test_build_witch_message_with_kill(self):
        """Test building witch message when someone is killed."""
        from src.websocket.werewolf_handlers import _build_witch_message

        killed = {"seat_number": 3, "display_name": "Player_3"}
        message = _build_witch_message(killed, True, True)

        assert "3号" in message
        assert "解药" in message
        assert "毒药" in message

    async def test_build_witch_message_peaceful_night(self):
        """Test building witch message for peaceful night."""
        from src.websocket.werewolf_handlers import _build_witch_message

        message = _build_witch_message(None, True, True)

        assert "平安夜" in message or "无人" in message


@pytest.mark.asyncio
class TestNotifyPlayerTurnNoSid:
    """Tests for player turn notifications when SID not found."""

    async def test_notify_werewolf_turn_no_sid(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test werewolf turn notification when player SID not found."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_werewolf_turn

            mock_get_sid.return_value = None  # No SID found

            await notify_werewolf_turn(
                room_code=sample_room_code,
                werewolf_player_ids=["werewolf_1"],
                alive_targets=sample_alive_players,
            )

            # Should not emit if SID not found
            mock_sio.emit.assert_not_called()

    async def test_notify_seer_turn_no_sid(
        self, mock_sio, sample_room_code, sample_alive_players
    ):
        """Test seer turn notification when player SID not found."""
        with patch('src.websocket.werewolf_handlers.sio', mock_sio), \
             patch('src.websocket.werewolf_handlers._get_sid_by_player_id') as mock_get_sid:
            from src.websocket.werewolf_handlers import notify_seer_turn

            mock_get_sid.return_value = None

            await notify_seer_turn(
                room_code=sample_room_code,
                seer_player_id="seer_1",
                alive_targets=sample_alive_players,
            )

            mock_sio.emit.assert_not_called()
