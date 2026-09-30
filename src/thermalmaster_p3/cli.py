import argparse
import json
import math
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import Camera, P3Error, FrameTimeoutError, list_devices
from .recording import SessionWriter, replay


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Unofficial Thermal Master P3 SDK')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('devices', help='List P3 devices and USB paths')
    for name in ('info', 'capture', 'record', 'viewer'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--serial')
        cmd.add_argument('--path', help='USB path reported by devices')
        if name != 'info':
            cmd.add_argument('--gain', choices=('high', 'low'), default='high')
        if name in ('capture', 'record'):
            cmd.add_argument('output')
        if name == 'record':
            cmd.add_argument('--duration', type=float, default=60)
        if name == 'viewer':
            cmd.add_argument('--range', type=float, nargs=2, metavar=('MIN_C', 'MAX_C'))
            cmd.add_argument('--rotate', type=int, choices=(0, 180), default=0, help='Display rotation; raw coordinates stay native')
    cmd = commands.add_parser('replay')
    cmd.add_argument('session')
    cmd.add_argument('--viewer', action='store_true')
    cmd.add_argument('--range', type=float, nargs=2, metavar=('MIN_C', 'MAX_C'))
    cmd.add_argument('--rotate', type=int, choices=(0, 180), default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == 'devices':
            print(json.dumps([asdict(x) for x in list_devices()], indent=2))
        elif args.command == 'replay':
            if args.viewer:
                from .viewer import run_viewer
                manifest = json.loads((Path(args.session) / 'manifest.json').read_text(encoding='utf-8'))
                source = 'SYNTHETIC REPLAY' if manifest.get('configuration', {}).get('synthetic') else 'REPLAY'
                run_viewer(frames=replay(args.session), source_label=source, limits=args.range, rotation=args.rotate)
            else:
                count = 0
                for frame in replay(args.session):
                    count += 1
                print(json.dumps({'frames': count}))
        else:
            if args.command == 'record' and (not math.isfinite(args.duration) or args.duration <= 0):
                parser.error('--duration must be positive and finite')
            with Camera(serial=args.serial, path=args.path) as camera:
                if args.command == 'info':
                    print(json.dumps(camera.info, indent=2))
                    return 0
                camera.start()
                camera.set_gain(args.gain)
                if args.command == 'capture':
                    frame = camera.read_frame()
                    with open(args.output, 'wb') as stream:
                        np.savez_compressed(stream, **asdict(frame), temperature_c=frame.temperature_c)
                    print('Saved radiometric frame to ' + args.output)
                elif args.command == 'record':
                    started = time.monotonic()
                    count = 0
                    with SessionWriter(args.output, {'device': camera.info, 'gain': camera.gain}) as writer:
                        try:
                            while time.monotonic() - started < args.duration:
                                try:
                                    frame = camera.read_frame(timeout=min(2.0, max(.001, args.duration - (time.monotonic() - started))))
                                except FrameTimeoutError:
                                    continue
                                writer.write(frame)
                                count += 1
                        finally:
                            elapsed = time.monotonic() - started
                            print(json.dumps({'frames': count, 'seconds': elapsed,
                                              'fps': count / max(elapsed, .001),
                                              'corrupt_candidates': camera.parser.corrupt_candidates,
                                              'counter_discontinuities': camera.parser.counter_discontinuities,
                                              'queue_drops': camera.parser.queue_drops,
                                              'timeouts': camera.timeouts}, indent=2))
                elif args.command == 'viewer':
                    from .viewer import run_viewer
                    run_viewer(camera=camera, limits=args.range, rotation=args.rotate)
        return 0
    except KeyboardInterrupt:
        return 130
    except (P3Error, ValueError, OSError, ImportError) as exc:
        print('p3: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
