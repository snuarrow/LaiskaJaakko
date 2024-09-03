# LaiskaJaakko

Development started on 07.06.2024, many things are still incomplete

Cheap Open Source WiFi Iot-sensor monitor platform

Features:
- Soil Moisture, Air Temperature & Humidity time series monitoring
- REST JSON endpoints for integrations
- Web user interface for stand-alone use
- React.js on Pi Pico W
- Configure WiFi via Pico hosted hotspot
- Cloud software-update from Git via Web-UI
- Time series graphs for each sensor in Web-UI
- Support for 3 plants per Pico for now

Features (work in progress):
- Remote server for remote use without virtual private networks

Requires following hardware (total cost ~9 euros / unit):
- Raspberry Pi Pico W
- AHT10 Temperature & humidity monitor
- 3x Analog 3.3v soil moisture sensor
- 3d-printed case

Build guide and printable 3D-models coming soon

Current simple UI:

<img src="https://github.com/snuarrow/LaiskaJaakko/blob/images-to-readme/media/ui-v2.png?raw=true" alt="Current UI" width="400"/>

Current version of unit assembled:

<img src="https://github.com/snuarrow/LaiskaJaakko/blob/images-to-readme/media/assembly-v3.jpeg?raw=true" alt="Current UI" width="400"/>


User Manual (BETA RELEASE):
- When led is blinking blue the sensor is in AP-mode, then connect to hotspot: SSID: iot, pass: laiskajaakko, then navigate to 192.168.4.1 and set your own wifi credentials
- Do some IT-wizardy and find out from which ip the sensor is found on your wifi subnet
- Open the ip with browser and enjoy
- One can delete configured WiFi credentials by pressing the WiFi Reset button for 5 seconds, then led should blink red and the sensor returns to blue blinking AP-mode
