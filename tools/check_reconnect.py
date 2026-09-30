"""Short manual unplug/replug check; waits for USB presence without streaming loops."""
import json
import time
from pathlib import Path

from thermalmaster_p3 import Camera, DeviceDisconnectedError, list_devices


def wait_for_presence(present, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bool(list_devices()) == present:
            return
        time.sleep(.5)
    raise TimeoutError('Expected P3 USB presence: ' + str(present))


def main():
    report = {'test': 'physical Windows unplug/replug', 'result': 'pending'}
    camera = Camera()
    try:
        camera.open()
        camera.start()
        camera.read_frame()
        camera.parser.ready.clear()
        print('READY: unplug P3, wait at least 8 seconds, then reconnect.', flush=True)
        wait_for_presence(False)
        try:
            camera.read_frame(timeout=1)
        except DeviceDisconnectedError:
            report['unplug_error'] = 'DeviceDisconnectedError'
        else:
            raise AssertionError('Unplug did not produce DeviceDisconnectedError')
        camera.close()
        print('Unplug detected. Waiting for reconnection.', flush=True)
        wait_for_presence(True)
        with Camera() as reopened:
            reopened.start()
            frame = reopened.read_frame()
            report.update(result='passed', shape=list(frame.raw.shape), firmware=reopened.info['firmware'])
        print(json.dumps(report), flush=True)
    finally:
        camera.close()
        Path('build/reconnect-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
