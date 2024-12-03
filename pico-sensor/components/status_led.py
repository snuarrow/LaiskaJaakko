import json
import random
from machine import Pin, PWM, Timer  # type: ignore
from time import sleep

class StatusLed:
    lit: bool = False

    def __init__(self, brightness: float = 0.01) -> None:
        self.brightness = brightness
        with open("config.json", "r") as f:
            led_config = json.load(f)["rgb_led"]
        self.blue_pin_number = led_config["blue_pin"]
        self.red_pin_number = led_config["red_pin"]
        self.green_pin_number = led_config["green_pin"]
        self.timer = Timer(-1)
        self.signal_power_on()
        #self.disco_start()
        #self.disco_stop()
        #self.disco_start()

    def _random_colour(self, timer: Timer = None) -> None:
        random_red = random.randint(0, int(65536 * self.brightness))
        random_green = random.randint(0, int(65536 * self.brightness))
        random_blue = random.randint(0, int(65536 * self.brightness))
        self.red.duty_u16(random_red)
        self.green.duty_u16(random_green)
        self.blue.duty_u16(random_blue)

    def signal_power_on(self) -> None:
        self.blue_pin = Pin(self.blue_pin_number)
        self.blue_pin.value(0)
        self.blue = PWM(self.blue_pin)
        self.blue.freq(1000)

        self.red_pin = Pin(self.red_pin_number)
        self.red_pin.value(0)
        self.red = PWM(self.red_pin)
        self.red.freq(1000)

        self.green_pin = Pin(self.green_pin_number)
        self.green_pin.value(0)
        self.green = PWM(self.green_pin)
        self.green.freq(1000)
        self.red.duty_u16(300)
        self.green.duty_u16(0)
        self.blue.duty_u16(0)

    def signal_cloud_update(self) -> None:
        self.disco_stop()
        self.red_pin = Pin(self.red_pin_number)
        self.green_pin = Pin(self.green_pin)
        self.blue_pin = Pin(self.blue_pin)
        self.blue_pin.value(1)
        sleep(1)
        self.green_pin.value(1)
        sleep(1)
        self.red_pin.value(1)
        sleep(2)
        self.red_pin.value(0)
        self.green_pin.value(0)
        self.blue_pin.value(0)
        sleep(0.5)
        for i in range(3):
            self.red_pin.value(1)
            self.green_pin.value(1)
            self.blue_pin.value(1)
            sleep(0.1)
            self.red_pin.value(0)
            self.green_pin.value(0)
            self.blue_pin.value(0)

    def signal_wifi_reset(self) -> None:
        self.disco_stop()
        self.red_pin = Pin(self.red_pin_number)
        for _ in range(10):
            self.red_pin.value(1)
            sleep(0.05)
            self.red_pin.value(0)
            sleep(0.2)

    def signal_wifi_set(self) -> None:
        self.disco_stop()
        self.green_pin = Pin(self.green_pin_number)
        for _ in range(10):
            self.green_pin.value(1)
            sleep(0.05)
            self.green_pin.value(0)
            sleep(0.2)

    def signal_cloud_update_error(self) -> None:
        self.disco_stop()
        self.red_pin = Pin(self.red_pin_number)
        for _ in range(10):
            self.red_pin.value(1)
            sleep(0.1)
            self.red_pin.value(0)
            sleep(0.2)

    def signal_cloud_update_ok(self) -> None:
        self.disco_stop()
        self.green_pin = Pin(self.green_pin_number)
        for _ in range(3):
            self.green_pin.value(1)
            sleep(0.05)
            self.green_pin.value(0)
            sleep(0.2)

    def _ap_mode_cycle(self, timer: Timer = None) -> None:
        if self.lit:
            self.red.duty_u16(0)
            self.green.duty_u16(0)
            self.blue.duty_u16(0)
            self.lit = False
        else:
            self.red.duty_u16(0)
            self.green.duty_u16(0)
            self.blue.duty_u16(1000)
            self.lit = True

    def ap_mode_start(self) -> None:
        self.blue_pin = Pin(self.blue_pin_number)
        self.blue_pin.value(0)
        self.blue = PWM(self.blue_pin)
        self.blue.freq(1000)

        self.red_pin = Pin(self.red_pin_number)
        self.red_pin.value(0)
        self.red = PWM(self.red_pin)
        self.red.freq(1000)

        self.green_pin = Pin(self.green_pin_number)
        self.green_pin.value(0)
        self.green = PWM(self.green_pin)
        self.green.freq(1000)

        self.lit = True
        if self.timer:
            self.timer.deinit()
        self.timer = Timer(-1)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self._ap_mode_cycle)

    def disco_start(self) -> None:
        self.blue_pin = Pin(self.blue_pin_number)
        self.blue_pin.value(0)
        self.blue = PWM(self.blue_pin)
        self.blue.freq(1000)

        self.red_pin = Pin(self.red_pin_number)
        self.red_pin.value(0)
        self.red = PWM(self.red_pin)
        self.red.freq(1000)

        self.green_pin = Pin(self.green_pin_number)
        self.green_pin.value(0)
        self.green = PWM(self.green_pin)
        self.green.freq(1000)

        self.lit = True
        if self.timer:
            self.timer.deinit()
        self.timer = Timer(-1)
        self.timer.init(period=1000, mode=Timer.PERIODIC, callback=self._random_colour)

    def disco_stop(self) -> None:
        self.lit = False
        self.timer.deinit()
        self.red_pin = Pin(self.red_pin_number, Pin.OUT)
        self.red_pin.value(0)
        self.green_pin = Pin(self.green_pin_number, Pin.OUT)
        self.green_pin.value(0)
        self.blue_pin = Pin(self.blue_pin_number, Pin.OUT)
        self.blue_pin.value(0)

    def value(self) -> bool:
        return self.lit