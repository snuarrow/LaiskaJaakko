# Build Guide

### Required Components
Make sure you have all following hardware in hand before starting the assembly.
- Raspberry Pi Pico W
- AHT10 Temperature & Humidity sensor with I2C bus
- 3x Soil moisture sensor units
- 3x Soil moisture sensing forks
- Minimum of 30cm of single threaded Ø0,6mm equipment wire
- 6x 2-pin harwin connectors and corresponding female pins
- Enough flat-cable to do 3x 50cm pair cables
- A Biltema USB-cable (24-4011 or 24-4012 or 24-4013)
- 3D-printed case with all 3 parts (case, lid, aht10-case)
- 2x 5mm m3 machine screws
- Common cathode (common ground) 4-pin rgb led
- 2-pin tactile panel switch

### Required tools
- Soldering iron and tin
- Small and sharp side cutters
- Preferably a desoldering iron for removing the moisture sensor pins. With some soldering expertise one can cope without
- Bench press
- Preferably a pair of Harwin connector crimping pliers. With some expertise one can cope with regular multitool pliers or similar

### Preparation of wiring
From the equipement wire, cut following pieces:
- 4x 22mm
- 2x 38mm
- 1x 27mm
- 6x 20mm
Peel 1.5mm of insulation on all wires except the 20mm ones, they should be peeled completely.

### Preparation of other components
- De-solder the existing 4-pin connectors from the Soil-Moisture sensor units. Leave 2-pin connectors as they are.
- Make sure the screws fit the 3D-printed body by screwing them in couple of times with the lid on.
- Flash micropython into the Pico and make sure the Pico is not defective. (power on when pressing the bootsel button, then pico should appear as a storage device on Linux computer. Then copy the micropython firmware to Pico). Make sure you can i.e. blink the led on the Pico using micropython to assure that the board is working.

### Build Process
Follow the exact order of the build process, otherwise you might cause some difficulties for yourself
1. Using bench press, be gentle not to ruin the insulation of the wires. Solder 4x 22mm wires to the AHT10, wires should be pointing up from the component side of the pcb
2. Insert the soldered assembly into the printed AHT10 case
3. Solder the AHT assembly to Pico pins 1,2,3,4 from the bottom side of pico. The AHT10 component side should face inside of pico.
4. Make a tight bend to AHT wires so that both pico and AHT pcb's are paraller. Ensure proper fit with the 3D printed case.
5. Solder the 2-pin switch on the component side of Pico to pins 5, 7.
6. Cut excess wires of the switch.
7. Solder in the RGB-led to pins 21,22,23,24. Ground pin is the 23. Make sure that the led is properly positioned in-line with pins and the center of the led should be between pins 22 and 23. Try getting the LED close enough to the Pico pcb.
8. Cut excess wires of the led.
9. Ensure the fit to the case at this point
10. Solder 38mm, 27mm and 38mm wires for each of the moisture-sensors A0 pins. Wires should be facing the component side of the pcb
11. Solder 20mm completely stripped wires for all of the three moisture sensors. They should be in vcc and gnd pins.
12. For the moisture sensor 1 make a first bend paraller to the longest edge of the pcb. Second bend should be 90 degrees left after the potentiometer position. Third bend should be upwards just before the peeled end
13. For the moisture sensor 3 make exact same bending steps, but the turn to left should be right
14. For the moisture sensor 2, the first bend is the same as in the 1 and 3, but second at the position just after the potentiometer should face up
15. When positioning the 3 moisture sensors next to each other, the bended wires should line up next to each other
16. Cut all excess wires from all moisture sensors and try to make the back of the pcb's as flat as possible.
17. Insert moisture sensor 1 gnd and vcc wires to Pico pins 18,19. and leave unsoldered. Solder the A0 wire to Pico pin 31.
18. Insert moisture sensor 2 gnd and vcc wires to Pico pins 13,14. and leave unsoldered. Solder the A0 wire to Pico pin 32.
19. Insert moisture sensor 3 gnd and vcc wires to Pico pins 8,9. and leave unsoldered. Solder the A0 wire to Pico pin 34.
20. Slightly bending all the unsoldered wires, make the assembly fit nicely into the 3D-printed case. Be gentle.
21. Whilst the assembly is correctly in the case, solder the vcc and gnd wires of moisture sensors to pico.
22. Cut excess wires
23. Put the lid on with screws
24. Prepare 3 pair cables with the 2 pin female harwin connectors, they should be some 50cm in lenght or whatever you prefer. So far at least 70cm lenght has been tested to work. Longer might or might not cause issues, report such if you go crazy with the sensor wires.
24. Connect usb cable to pico and a Linux computer

### Flashing the software
1. Copy all necessary files to Pico root, one can use i.e. Thonny or similar:
- main.py
- typing.py
- version.json
- config.json
- ap_index.html
- components folder from pico-sensor folder
- dist folder from pico-sensor/laiska-frontend folder
2. Power cycle Pico and it should work
