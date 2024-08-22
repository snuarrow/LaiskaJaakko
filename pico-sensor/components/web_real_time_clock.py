from machine import Timer  # type: ignore
from typing import Tuple, Optional
import socket, struct, utime  # type: ignore
from time import ticks_ms, ticks_diff  # type: ignore


class WebRealTimeClock:
    NTP_DELTA = 2208988800  # Time difference between 1900 and 1970 (in seconds)
    NTP_SERVER = "pool.ntp.org"

    def __init__(self) -> None:
        self.unix_time, _ = self.get_ntp_time()  # TODO: improve flow, this is ugly
        self.start_time = ticks_ms()
        self.timer = Timer(-1)
        self.update_time_from_ntp()
        self.timer.init(
            period=3600000, mode=Timer.PERIODIC, callback=self.update_time_from_ntp
        )

    def get_ntp_time(self) -> Tuple[int, Optional[str]]:  # time, error
        try:
            ntp_query = b"\x1b" + 47 * b"\0"
            addr = socket.getaddrinfo(self.NTP_SERVER, 123)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.sendto(ntp_query, addr)
            msg = s.recv(48)
            s.close()
            val = struct.unpack("!I", msg[40:44])[0]
            return val - self.NTP_DELTA, None
        except:
            return (
                946684800,
                "Failed to Update NTP time, defaulting to 1.1.2000",
            )  # Default to Jan 1, 2000

    def update_time_from_ntp(self, timer: Timer = None) -> None:
        try:
            new_unix_time, error = self.get_ntp_time()
            if error:
                print(error)
                return
            self.start_time = ticks_ms()
            self.unix_time = new_unix_time
            print("NTP Time Updated:", new_unix_time)
            if new_unix_time < 0:
                print(
                    "NTP time is negative, defaulting to Jan 1 2000"
                )  # TODO: this is a temporary fix, find out why NTP time is occasionally negative
                self.unix_time = 946684800
        except Exception as e:
            print("Failed to update NTP time:", e)
            self.unix_time = 946684800  # Default to Jan 1, 2000

    def get_current_unix_time(self) -> int:
        elapsed_time = int(ticks_diff(ticks_ms(), self.start_time) // 1000)
        current_unix_time = self.unix_time + elapsed_time
        return current_unix_time

    def get_pretty_time(self) -> str:
        try:
            current_unix_time = self.get_current_unix_time()
            adjusted_unix_time = current_unix_time + 3 * 3600
            datetime_tuple = utime.localtime(adjusted_unix_time)
            pretty_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
                *datetime_tuple[:6]
            )
            return pretty_time
        except Exception as e:
            if "OverflowError" in str(e):
                print("OverflowError: overflow converting long int to machine word")
                return "2000-01-01 00:00:00"
            raise e
