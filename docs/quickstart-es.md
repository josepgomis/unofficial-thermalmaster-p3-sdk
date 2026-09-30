# Guía rápida

SDK no oficial e independiente para Thermal Master P3. Python ≥3.8, Windows y Linux; visor y ROS 2 opcionales.

Esta versión 0.1.0 es alpha. Hay pruebas automatizadas, pero todavía no se ha comprobado la captura física: Windows identifica la cámara y muestra una interfaz sin controlador instalado.

Desde la carpeta del repositorio:

```sh
python -m pip install .
p3 devices
p3 info
p3 capture frame.npz
```

Antes de capturar, sigue la [guía USB](usb.md): WinUSB para las interfaces de la P3 en Windows, o libusb y permisos udev en Linux. El SDK no sustituye controladores automáticamente.

```python
from thermalmaster_p3 import Camera

with Camera() as camera:
    camera.start()
    temperaturas = camera.read_frame().temperature_c
    print(temperaturas[96, 128])
```

Para el visor: `python -m pip install ".[viewer]"` y `p3 viewer`. Para grabar: `p3 record sessions/prueba --duration 60`. Para reproducir: `p3 replay sessions/prueba --viewer`.

Las temperaturas no dependen de la paleta del visor. Las marcas de tiempo corresponden a recepción en el PC, no a exposición sincronizada. Consulta la [guía ROS 2](ros2.md) para Foxy, Humble y Jazzy.
