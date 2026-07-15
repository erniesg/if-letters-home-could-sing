"""Minimal implementation of the AppLoad backend socket contract."""

from __future__ import annotations

import socket
import struct
import sys
from typing import Optional, Sequence, Tuple

from .adapter import MESSAGE_OPEN, FixtureBackend, OutboundMessage


MAX_PACKET_SIZE = 10_485_760
MSG_SYSTEM_TERMINATE = 0xFFFFFFFF
MSG_SYSTEM_NEW_COORDINATOR = 0xFFFFFFFE
HEADER = struct.Struct("=II")


class ProtocolError(ValueError):
    """Raised for malformed AppLoad frames."""


def receive_message(connection: socket.socket) -> Optional[Tuple[int, str]]:
    header = connection.recv(HEADER.size + 1)
    if not header:
        return None
    if len(header) != HEADER.size:
        raise ProtocolError("AppLoad message header has the wrong size")
    message_type, length = HEADER.unpack(header)
    if length > MAX_PACKET_SIZE:
        raise ProtocolError("AppLoad message exceeds the protocol limit")
    if length == 0:
        return message_type, ""
    contents = connection.recv(length + 1)
    if len(contents) != length:
        raise ProtocolError("AppLoad message body has the wrong size")
    try:
        return message_type, contents.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProtocolError("AppLoad message body is not UTF-8") from error


def send_message(connection: socket.socket, message: OutboundMessage) -> None:
    contents = message.contents.encode("utf-8")
    if len(contents) > MAX_PACKET_SIZE:
        raise ProtocolError("AppLoad response exceeds the protocol limit")
    _send_packet(connection, HEADER.pack(message.message_type, len(contents)))
    if contents:
        _send_packet(connection, contents)


def _send_packet(connection: socket.socket, contents: bytes) -> None:
    if connection.send(contents) != len(contents):
        raise ProtocolError("AppLoad packet was only partially sent")


def run_backend(socket_path: str, backend: Optional[FixtureBackend] = None) -> None:
    """Connect to the temporary socket supplied as AppLoad backend argv[1]."""

    fixture_backend = backend or FixtureBackend()
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
        connection.connect(socket_path)
        while True:
            incoming = receive_message(connection)
            if incoming is None:
                return
            message_type, contents = incoming
            if message_type == MSG_SYSTEM_TERMINATE:
                return
            if message_type == MSG_SYSTEM_NEW_COORDINATOR:
                responses = fixture_backend.dispatch(MESSAGE_OPEN)
            else:
                responses = fixture_backend.dispatch(message_type, contents)
            for response in responses:
                send_message(connection, response)


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = tuple(argv if argv is not None else sys.argv[1:])
    if len(arguments) != 1:
        print("usage: python3 -m tablet_app.protocol <appload-socket>", file=sys.stderr)
        return 2
    try:
        run_backend(arguments[0])
    except (OSError, ProtocolError) as error:
        print(f"backend unavailable: {type(error).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
