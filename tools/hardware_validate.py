"""Physical capture endurance check. Reports metrics, not a calibration certificate."""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from thermalmaster_p3 import Camera, FrameTimeoutError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=1800)
    parser.add_argument('--report', default='build/hardware-validation.json')
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error('duration must be positive')
    report = {'started_utc': datetime.now(timezone.utc).isoformat(),
              'platform': platform.platform(), 'python': platform.python_version(),
              'requested_seconds': args.duration, 'timestamp_origin': 'host reception',
              'controls': [], 'intervals': []}
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    started, count, last_log = time.monotonic(), 0, 0.
    schedule = [(5., 'gain_low'), (10., 'gain_high'), (20., 'nuc')]
    camera = Camera()
    try:
        camera.open()
        report.update(model=camera.info['model'], firmware=camera.info['firmware'])
        camera.start()
        camera.set_gain('high')
        started = time.monotonic()
        while time.monotonic() - started < args.duration:
            elapsed = time.monotonic() - started
            if schedule and elapsed >= schedule[0][0]:
                _, action = schedule.pop(0)
                if action == 'nuc':
                    camera.trigger_nuc()
                else:
                    camera.set_gain(action.split('_')[1])
                report['controls'].append({'elapsed_seconds': elapsed, 'action': action,
                                           'result': 'acknowledged'})
            try:
                frame = camera.read_frame(timeout=min(.5, max(.001, args.duration - elapsed)))
            except FrameTimeoutError:
                continue
            assert frame.raw.shape == (192, 256) and frame.ir.shape == (192, 256)
            count += 1
            if elapsed - last_log >= 60:
                interval = {'elapsed_seconds': elapsed, 'frames': count,
                            'average_fps': count / max(elapsed, .001)}
                report['intervals'].append(interval)
                report.update(result='in_progress', **interval,
                              timeouts=camera.timeouts,
                              corrupt_candidates=camera.parser.corrupt_candidates,
                              queue_drops=camera.parser.queue_drops,
                              counter_discontinuities=camera.parser.counter_discontinuities)
                temporary = output.with_suffix('.tmp')
                temporary.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
                temporary.replace(output)
                print(json.dumps(interval), flush=True)
                last_log = elapsed
        report['result'] = 'passed' if count else 'failed: no frames'
    except KeyboardInterrupt:
        report['result'] = 'stopped_by_user'
        raise
    except Exception as exc:
        report['result'] = 'failed'
        report['error'] = str(exc)
        raise
    finally:
        elapsed = time.monotonic() - started
        report.update(seconds=elapsed, frames=count, fps=count / max(elapsed, .001),
                      timeouts=camera.timeouts, corrupt_candidates=camera.parser.corrupt_candidates,
                      queue_drops=camera.parser.queue_drops,
                      counter_discontinuities=camera.parser.counter_discontinuities,
                      discarded_bytes=camera.parser.discarded_bytes)
        camera.close()
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
