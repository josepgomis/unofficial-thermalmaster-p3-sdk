# Protocol basis

The transport is an original implementation based on [jvdillon/p3-ir-camera's public P3 protocol documentation](https://github.com/jvdillon/p3-ir-camera/blob/main/P3_PROTOCOL.md), read on 2026-09-30. No vendor DLL, firmware binary, or upstream driver source is bundled.

Only P3 `3474:45a2`, native 256x192, is supported. The advertised enhanced display resolution is not the raw sensor grid. Tests exercise documented packet facts, including command checksum vectors and mixed byte order: command IDs use their documented byte sequence, while numeric parameters and CRC use little endian.

The parser checks the expected payload length, start/end sync pairing and matching first marker counter. It preserves all marker counters and original metadata. It can receive arbitrary read fragments and recover after corrupt transfers. The unusual NUC transition is deliberately discarded; subsequent valid frames are delivered.

Physical tests on firmware `00.00.02.18` showed status `0x03` after write-only gain and NUC commands. The SDK accepts `0x02` or `0x03` for those commands, while register/stream reads still require the write `0x02`, data read, then `0x03` sequence. Unknown status bytes remain errors. See the [validation report](validation.md).

An acknowledged command is not proof of measurement accuracy. Register access, arbitrary vendor writes, firmware changes and environmental correction algorithms are not public APIs in v1.
