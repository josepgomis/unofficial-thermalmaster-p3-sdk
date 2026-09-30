import struct

import numpy as np
import pytest

from thermalmaster_p3 import raw_to_celsius
from thermalmaster_p3.protocol import FrameParser, PAYLOAD_SIZE, command


def wire(counter=123, clock=40, value=19082, odd=False):
    pixels = np.zeros((386, 256), dtype='<u2')
    pixels[:192] = 0x12ab
    pixels[192:194] = 1234
    pixels[194:] = value
    start = struct.pack('<BBIIH', 12, 0x8d if odd else 0x8c, counter, 0, clock)
    end = struct.pack('<BBIIH', 12, 0x8f if odd else 0x8e, counter, 0, (clock + 40) % 2048)
    return start + pixels.tobytes() + end


@pytest.mark.parametrize('size', [1, 11, 12, 16384, 197632, 300000])
def test_fragmented_frames(size):
    parser = FrameParser()
    data = wire()
    for offset in range(0, len(data), size):
        parser.feed(data[offset:offset + size])
    frame = parser.pop()
    assert frame.raw.shape == (192, 256)
    assert frame.raw.dtype == np.uint16
    assert np.all(frame.raw == 19082)
    assert np.all(frame.ir == 0xab)
    assert np.all(frame.metadata == 1234)
    assert frame.start_counters[0] == 123
    assert frame.monotonic_ns > 0 and frame.utc_ns > 0
    assert parser.pop() is None


def test_corrupt_marker_truncation_and_recovery():
    bad = bytearray(wire())
    bad[-10] ^= 1
    parser = FrameParser()
    parser.feed(b'garbage' + bytes(bad) + wire()[:9000] + wire(counter=124, odd=True))
    frame = parser.pop()
    assert frame.start_counters[0] == 124
    assert parser.corrupt_candidates >= 2
    assert parser.discarded_bytes > 0


def test_nuc_transition_discarded_then_valid_frame():
    original = wire()
    # Documented NUC pattern: 9204 extra bytes and an inserted second marker.
    nuc = original[:12] + original[12:9216] + original[12:12 + 195584]
    nuc += original[:12] + original[12 + 195584:-12] + original[-12:]
    parser = FrameParser()
    parser.feed(nuc + wire(counter=999, odd=True))
    frame = parser.pop()
    assert frame.start_counters[0] == 999
    assert parser.corrupt_candidates > 0


def test_owned_arrays_and_bounded_queue():
    parser = FrameParser()
    parser.feed(wire())
    frame = parser.pop()
    parser.feed(wire(value=20000) * 4)
    assert np.all(frame.raw == 19082)
    assert len(parser.ready) == 2
    assert parser.queue_drops == 2
    assert len(parser.buffer) < PAYLOAD_SIZE + 24


def test_counter_wrap_and_discontinuity():
    parser = FrameParser()
    parser.feed(wire(clock=2008))
    parser.feed(wire(counter=124, clock=0))
    assert parser.counter_discontinuities == 0
    parser.feed(wire(counter=125, clock=80))
    assert parser.counter_discontinuities == 1


def test_conversion_and_documented_commands():
    result = raw_to_celsius(np.array([0, 17482, 19082], dtype=np.uint16))
    assert result.dtype == np.float32
    np.testing.assert_allclose(result, [-273.15, .00625, 25.00625], atol=2e-5)
    assert command(0x0101, 0x81, 1, 30).hex() == '0101810001000000000000001e0000004f90'
    assert command(0x012f, 0x81, length=1).hex() == '012f81000000000000000000010000004930'
    assert command(0x0136, 0x43).hex() == '01364300000000000000000000000000cd0b'
