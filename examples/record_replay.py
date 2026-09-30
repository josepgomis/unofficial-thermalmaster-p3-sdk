from thermalmaster_p3 import Camera
from thermalmaster_p3.recording import SessionWriter, replay

with Camera() as camera:
    camera.start()
    with SessionWriter('sessions/example', {'device': camera.info}) as writer:
        for _ in range(100):
            writer.write(camera.read_frame())

for frame in replay('sessions/example'):
    print(frame.sequence, frame.utc_ns, frame.temperature_c.mean())
