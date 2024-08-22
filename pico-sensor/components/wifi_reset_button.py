import time
from machine import Pin, Timer, reset  # type: ignore
from components.status_led import StatusLed
from os import remove

WIFI_CONFIG_FILE = "wifi_config.json"

def delete_wifi_config() -> None:
    try:
        remove(WIFI_CONFIG_FILE)
        print("Configuration file deleted successfully")
    except OSError as e:
        print("Error deleting configuration file:", e)

class WifiResetButton():
    def __init__(self, power_pin: int, signal_pin: int, status_led: StatusLed, pico_led: Pin) -> None:
        self.pico_led = pico_led
        self.wifi_reset_button_power_pin = Pin(power_pin, Pin.OUT)
        self.wifi_reset_button_power_pin.value(1)
        self.wifi_reset_button_signal_pin = Pin(signal_pin, Pin.IN, Pin.PULL_DOWN)
        self.debounced: bool = False
        self.pressed: bool = False
        self.DEBOUNCE_TIME = 70
        self.debounce_timer = Timer()
        self.wifi_reset_button_signal_pin.irq(
            trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
            handler=lambda pin: (
                self._handle_button_press()
                if pin.value() == 1
                else self._handle_button_release()
            ),
        )
        self.rising_time_ms = 0
        self.status_led = status_led

    def _reset_debounce(self) -> None:
        self.debounced = False

    def _handle_button_press(self) -> None:
        if not self.debounced and not self.pressed:
            self.debounced = True
            self.pico_led.value(1)
            self.pressed = True
            self.rising_time_ms = time.ticks_ms()  # type: ignore
            self.debounce_timer.init(
                mode=Timer.ONE_SHOT,
                period=self.DEBOUNCE_TIME,
                callback=self._reset_debounce(),  # type: ignore
            )

    def _handle_button_release(self) -> None:
        global led
        if not self.debounced and self.pressed:
            self.debounced = True
            self.pico_led.value(0)
            self.pressed = False
            elapsed_time_ms = time.ticks_diff(time.ticks_ms(), self.rising_time_ms)  # type: ignore
            if elapsed_time_ms > 3000:
                self.status_led.signal_wifi_reset()
                delete_wifi_config()
                reset()
            self.debounce_timer.init(
                mode=Timer.ONE_SHOT,
                period=self.DEBOUNCE_TIME,
                callback=self._reset_debounce(),  # type: ignore
            )