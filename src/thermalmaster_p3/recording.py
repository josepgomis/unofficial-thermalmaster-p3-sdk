"""Versioned radiometric sessions. Files are committed using atomic renames."""
import json
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .frame import Frame

FIELDS = ('raw', 'ir', 'metadata', 'sequence', 'monotonic_ns', 'utc_ns',
          'start_counters', 'end_counters')


class SessionWriter:
    def __init__(self, directory, configuration: Optional[dict] = None, block_size: int = 100):
        if block_size <= 0:
            raise ValueError('block_size must be positive')
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=False)
        self.block_size = block_size
        self.pending = []
        self.closed = False
        self.manifest = {'format': 'thermalmaster-p3', 'version': 1,
                         'width': 256, 'height': 192, 'raw_units': '1/64 kelvin',
                         'timestamp_source': 'host reception',
                         'configuration': configuration or {}, 'blocks': [], 'frames': 0}
        self._manifest()

    def _manifest(self):
        temporary = self.path / 'manifest.json.tmp'
        temporary.write_text(json.dumps(self.manifest, indent=2), encoding='utf-8')
        temporary.replace(self.path / 'manifest.json')

    def write(self, frame: Frame):
        if self.closed:
            raise ValueError('Session is closed')
        # Snapshot at write time; callers may reuse or modify their own arrays.
        self.pending.append({key: np.array(getattr(frame, key), copy=True) for key in FIELDS})
        if len(self.pending) >= self.block_size:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        name = 'block-{:06d}.npz'.format(len(self.manifest['blocks']))
        temporary = self.path / (name + '.tmp')
        values = {key: np.stack([frame[key] for frame in self.pending]) for key in FIELDS}
        with temporary.open('wb') as stream:
            np.savez_compressed(stream, **values)
        temporary.replace(self.path / name)
        self.manifest['blocks'].append(name)
        self.manifest['frames'] += len(self.pending)
        self._manifest()
        self.pending.clear()

    def close(self):
        if not self.closed:
            self.flush()
            self.closed = True

    def event(self, name: str, values: dict):
        """Record a control change at host time without modifying measurements."""
        import time
        if self.closed:
            raise ValueError('Session is closed')
        self.manifest.setdefault('events', []).append({'name': name, 'values': values,
            'after_frames': self.manifest['frames'] + len(self.pending),
            'monotonic_ns': time.monotonic_ns(), 'utc_ns': time.time_ns()})
        self._manifest()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def replay(directory) -> Iterator[Frame]:
    path = Path(directory)
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'thermalmaster-p3' or manifest.get('version') != 1:
        raise ValueError('Unsupported session format/version')
    for name in manifest['blocks']:
        if Path(name).name != name or not name.endswith('.npz'):
            raise ValueError('Invalid block filename')
        with np.load(path / name, allow_pickle=False) as archive:
            data = {key: archive[key] for key in FIELDS}
            count = len(data['sequence'])
            expected = {'raw': (count, 192, 256), 'ir': (count, 192, 256),
                        'metadata': (count, 2, 256), 'start_counters': (count, 3),
                        'end_counters': (count, 3), 'sequence': (count,),
                        'monotonic_ns': (count,), 'utc_ns': (count,)}
            if any(data[key].shape != shape for key, shape in expected.items()):
                raise ValueError('Invalid session block dimensions')
            for i in range(count):
                yield Frame(data['raw'][i].copy(), data['ir'][i].copy(),
                            data['metadata'][i].copy(), int(data['sequence'][i]),
                            int(data['monotonic_ns'][i]), int(data['utc_ns'][i]),
                            tuple(int(x) for x in data['start_counters'][i]),
                            tuple(int(x) for x in data['end_counters'][i]))
