# Guía rápida

SDK no oficial e independiente para Thermal Master P3. Python ≥3.8, Windows y Linux; visor y ROS 2 opcionales.

Esta versión 0.1.0 es alpha. La P3 real ya entrega matrices e imágenes en Windows mediante WinUSB. Consulta los resultados medidos en la [validación](validation.md); las pruebas físicas en Linux y la exactitud absoluta siguen sin certificarse.

Instalación directa desde GitHub (Python ≥3.8 y Git):

```sh
python -m pip install "git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v0.1.0"
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

Para el visor:

```sh
python -m pip install "unofficial-thermalmaster-p3[viewer] @ git+https://github.com/josepgomis/unofficial-thermalmaster-p3-sdk.git@v0.1.0"
p3 viewer --rotate 180
```

Usa `--rotate 180` si tu montaje deja la imagen invertida. Solo cambia la presentación: las matrices y coordenadas siguen siendo las originales. Desde un checkout puedes instalar con `python -m pip install ".[viewer]"`.

Arrastra para medir una ROI; `c` la borra. `p` cambia la paleta, `a` alterna escala automática/fija, `i` exporta PNG, `s` guarda datos radiométricos, `r` graba, `n` pide NUC, `g` cambia ganancia y `q` cierra.

```sh
p3 record sessions/prueba --duration 60
p3 replay sessions/prueba --viewer --rotate 180 --range 15 60
```

Para probar sin cámara, descarga `p3-real-sample.zip` de la release alpha, extrae el archivo y ejecuta `p3 replay p3-real-sample --viewer --rotate 180`. Son datos reales; PyPI todavía no está publicado. Véanse [visor e imágenes](viewer.md), [ejemplos](examples.md) y [grabación/replay](recording.md).

Las temperaturas no dependen de la paleta del visor. Las marcas de tiempo corresponden a recepción en el PC, no a exposición sincronizada. Consulta la [guía ROS 2](ros2.md) para Foxy, Humble y Jazzy.
