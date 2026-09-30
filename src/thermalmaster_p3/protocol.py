"""Original framing implementation from publicly documented protocol facts."""
import struct
import time
from collections import deque
from typing import Optional

import numpy as np

from .frame import Frame

VID, PID = 0x3474, 0x45A2
WIDTH, HEIGHT = 256, 192
PAYLOAD_SIZE = WIDTH * (2 * HEIGHT + 2) * 2
WIRE_SIZE = PAYLOAD_SIZE + 24


def command(kind: int, parameter: int, register: int = 0, length: int = 0) -> bytes:
    # Command IDs are written in documented byte order (01 2f / 01 36),
    # whereas numeric parameters, register, length and CRC are little endian.
    data = struct.pack('>H', kind) + struct.pack('<HH6xHH', parameter, register, length, 0)
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xffff
    return data + struct.pack('<H', crc)


class FrameParser:
    """Bounded parser. Drops malformed NUC frames and resumes at valid framing."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.ready = deque(maxlen=2)
        self.sequence = 0
        self.corrupt_candidates = 0
        self.discarded_bytes = 0
        self.queue_drops = 0
        self.counter_discontinuities = 0
        self.previous_end = None

    def feed(self, chunk: bytes) -> None:
        self.buffer.extend(chunk)
        while True:
            a, b = self.buffer.find(b'\x0c\x8c'), self.buffer.find(b'\x0c\x8d')
            candidates = [i for i in (a, b) if i >= 0]
            if not candidates:
                discard = max(0, len(self.buffer) - 1)
                self.discarded_bytes += discard
                del self.buffer[:discard]
                return
            index = min(candidates)
            self.discarded_bytes += index
            del self.buffer[:index]
            if len(self.buffer) < WIRE_SIZE:
                return
            end = 12 + PAYLOAD_SIZE
            start_counts = struct.unpack_from('<IIH', self.buffer, 2)
            end_counts = struct.unpack_from('<IIH', self.buffer, end + 2)
            if (self.buffer[end] != 12 or
                    self.buffer[end + 1] != self.buffer[1] + 2 or
                    start_counts[0] != end_counts[0]):
                self.corrupt_candidates += 1
                self.discarded_bytes += 1
                del self.buffer[0]
                continue
            pixels = np.frombuffer(bytes(self.buffer[12:end]), dtype='<u2').reshape(386, WIDTH)
            frame = Frame(pixels[194:].copy(), (pixels[:192] & 255).astype(np.uint8),
                          pixels[192:194].copy(), self.sequence, time.monotonic_ns(),
                          time.time_ns(), start_counts, end_counts)
            if self.previous_end is not None and self.previous_end != start_counts[2]:
                self.counter_discontinuities += 1
            self.previous_end = end_counts[2]
            self.sequence += 1
            if len(self.ready) == self.ready.maxlen:
                self.queue_drops += 1
            self.ready.append(frame)
            del self.buffer[:WIRE_SIZE]

    def pop(self) -> Optional[Frame]:
        return self.ready.popleft() if self.ready else None
