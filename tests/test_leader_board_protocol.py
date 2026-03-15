# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Tests for the wire protocol frame parsing and serialization."""

from __future__ import annotations

import json

import pytest

from leader_board.protocol import (
    AckFrame,
    AuthFrame,
    AuthOkFrame,
    ChallengeFrame,
    ChannelsFrame,
    ChannelsListFrame,
    ErrorFrame,
    InvalidFrameError,
    MessageFrame,
    RegisterSwarmFrame,
    SendFrame,
    SwarmInfoFrame,
    SwarmInfoResponseFrame,
    WatchFrame,
    parse_client_frame,
    serialize_server_frame,
)


# ---------------------------------------------------------------------------
# parse_client_frame
# ---------------------------------------------------------------------------


class TestParseClientFrame:
    def test_parse_auth_frame(self) -> None:
        data = json.dumps({"type": "auth", "swarm": "s1", "signature": "aabb"})
        frame = parse_client_frame(data)
        assert isinstance(frame, AuthFrame)
        assert frame.swarm == "s1"
        assert frame.signature == "aabb"

    def test_parse_register_swarm_frame(self) -> None:
        data = json.dumps(
            {"type": "register_swarm", "swarm": "s1", "public_key": "ccdd"}
        )
        frame = parse_client_frame(data)
        assert isinstance(frame, RegisterSwarmFrame)
        assert frame.swarm == "s1"
        assert frame.public_key == "ccdd"

    def test_parse_watch_frame(self) -> None:
        data = json.dumps(
            {"type": "watch", "channel": "ch1", "swarm": "s1", "cursor": 42}
        )
        frame = parse_client_frame(data)
        assert isinstance(frame, WatchFrame)
        assert frame.channel == "ch1"
        assert frame.swarm == "s1"
        assert frame.cursor == 42

    def test_parse_send_frame(self) -> None:
        data = json.dumps(
            {"type": "send", "channel": "ch1", "swarm": "s1", "body": "dGVzdA=="}
        )
        frame = parse_client_frame(data)
        assert isinstance(frame, SendFrame)
        assert frame.body == "dGVzdA=="

    def test_parse_channels_frame(self) -> None:
        data = json.dumps({"type": "channels", "swarm": "s1"})
        frame = parse_client_frame(data)
        assert isinstance(frame, ChannelsFrame)
        assert frame.swarm == "s1"

    def test_parse_swarm_info_frame(self) -> None:
        data = json.dumps({"type": "swarm_info", "swarm": "s1"})
        frame = parse_client_frame(data)
        assert isinstance(frame, SwarmInfoFrame)
        assert frame.swarm == "s1"

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises(InvalidFrameError, match="Malformed JSON"):
            parse_client_frame("not json {{{")

    def test_parse_unknown_type_raises(self) -> None:
        data = json.dumps({"type": "unknown_type"})
        with pytest.raises(InvalidFrameError, match="Unknown frame type"):
            parse_client_frame(data)

    def test_parse_missing_type_raises(self) -> None:
        data = json.dumps({"swarm": "s1"})
        with pytest.raises(InvalidFrameError, match="Missing 'type' field"):
            parse_client_frame(data)

    def test_parse_missing_fields_raises(self) -> None:
        data = json.dumps({"type": "watch", "channel": "ch1"})
        with pytest.raises(InvalidFrameError, match="Missing required field"):
            parse_client_frame(data)

    def test_parse_non_object_raises(self) -> None:
        with pytest.raises(InvalidFrameError, match="JSON object"):
            parse_client_frame('"just a string"')


# ---------------------------------------------------------------------------
# serialize_server_frame
# ---------------------------------------------------------------------------


class TestSerializeServerFrame:
    def test_serialize_challenge_frame(self) -> None:
        frame = ChallengeFrame(nonce="aa" * 32)
        result = json.loads(serialize_server_frame(frame))
        assert result["type"] == "challenge"
        assert result["nonce"] == "aa" * 32

    def test_serialize_auth_ok_frame(self) -> None:
        result = json.loads(serialize_server_frame(AuthOkFrame()))
        assert result == {"type": "auth_ok"}

    def test_serialize_message_frame(self) -> None:
        frame = MessageFrame(
            channel="ch1",
            position=5,
            body="dGVzdA==",
            sent_at="2026-03-15T14:30:00Z",
        )
        result = json.loads(serialize_server_frame(frame))
        assert result["type"] == "message"
        assert result["channel"] == "ch1"
        assert result["position"] == 5
        assert result["body"] == "dGVzdA=="
        assert result["sent_at"] == "2026-03-15T14:30:00Z"

    def test_serialize_ack_frame(self) -> None:
        frame = AckFrame(channel="ch1", position=3)
        result = json.loads(serialize_server_frame(frame))
        assert result == {"type": "ack", "channel": "ch1", "position": 3}

    def test_serialize_channels_list_frame(self) -> None:
        frame = ChannelsListFrame(
            channels=[{"name": "ch1", "head_position": 5, "oldest_position": 1}]
        )
        result = json.loads(serialize_server_frame(frame))
        assert result["type"] == "channels_list"
        assert len(result["channels"]) == 1
        assert result["channels"][0]["name"] == "ch1"

    def test_serialize_swarm_info_response_frame(self) -> None:
        frame = SwarmInfoResponseFrame(
            swarm="s1", created_at="2026-03-15T14:30:00Z"
        )
        result = json.loads(serialize_server_frame(frame))
        assert result["type"] == "swarm_info"
        assert result["swarm"] == "s1"
        assert result["created_at"] == "2026-03-15T14:30:00Z"

    def test_serialize_error_frame(self) -> None:
        frame = ErrorFrame(code="auth_failed", message="bad sig")
        result = json.loads(serialize_server_frame(frame))
        assert result == {
            "type": "error",
            "code": "auth_failed",
            "message": "bad sig",
        }

    def test_serialize_error_frame_with_earliest_position(self) -> None:
        frame = ErrorFrame(
            code="cursor_expired",
            message="Cursor expired",
            earliest_position=42,
        )
        result = json.loads(serialize_server_frame(frame))
        assert result["earliest_position"] == 42

    def test_serialize_error_frame_without_earliest_position(self) -> None:
        frame = ErrorFrame(code="auth_failed", message="bad sig")
        result = json.loads(serialize_server_frame(frame))
        assert "earliest_position" not in result


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Verify that all client frame types can be serialized back."""

    @pytest.mark.parametrize(
        "json_str,expected_type",
        [
            (
                '{"type":"auth","swarm":"s","signature":"aa"}',
                AuthFrame,
            ),
            (
                '{"type":"register_swarm","swarm":"s","public_key":"bb"}',
                RegisterSwarmFrame,
            ),
            (
                '{"type":"watch","channel":"c","swarm":"s","cursor":0}',
                WatchFrame,
            ),
            (
                '{"type":"send","channel":"c","swarm":"s","body":"dGVzdA=="}',
                SendFrame,
            ),
            ('{"type":"channels","swarm":"s"}', ChannelsFrame),
            ('{"type":"swarm_info","swarm":"s"}', SwarmInfoFrame),
        ],
    )
    def test_round_trip_all_client_frame_types(
        self, json_str: str, expected_type: type
    ) -> None:
        frame = parse_client_frame(json_str)
        assert isinstance(frame, expected_type)
