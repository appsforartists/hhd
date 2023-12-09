import select
import time
from typing import Sequence

from hhd.controller.base import Event, Multiplexer
from hhd.controller.physical.evdev import GenericGamepadEvdev
from hhd.controller.physical.hidraw import GenericGamepadHidraw
from hhd.controller.physical.imu import AccelImu, GyroImu
from hhd.controller.virtual.ds5 import DualSense5Edge
from hhd.device.legion_go import (
    LGO_RAW_INTERFACE_BTN_ESSENTIALS,
    LGO_RAW_INTERFACE_BTN_MAP,
    LGO_RAW_INTERFACE_CONFIG_MAP,
    LGO_TOUCHPAD_AXIS_MAP,
    LGO_TOUCHPAD_BUTTON_MAP,
    SelectivePasshtrough,
)


def controller_loop():
    p = DualSense5Edge()

    a = AccelImu()
    b = GyroImu()
    c = GenericGamepadEvdev([0x17EF], [0x6182], "Generic X-Box pad")
    d = GenericGamepadEvdev(
        [0x17EF],
        [0x6182],
        ["  Legion Controller for Windows  Touchpad"],
        btn_map=LGO_TOUCHPAD_BUTTON_MAP,
        axis_map=LGO_TOUCHPAD_AXIS_MAP,
        aspect_ratio=1,
    )
    e = SelectivePasshtrough(
        GenericGamepadHidraw(
            vid=[0x17EF],
            pid=[
                0x6182,  # XINPUT
                0x6183,  # DINPUT
                0x6184,  # Dual DINPUT
                0x6185,  # FPS
            ],
            usage_page=[0xFFA0],
            usage=[0x0001],
            report_size=64,
            axis_map={},
            btn_map=LGO_RAW_INTERFACE_BTN_MAP,
            config_map=LGO_RAW_INTERFACE_CONFIG_MAP,
        )
    )
    # Mute keyboard shortcuts, mute
    f = GenericGamepadEvdev(
        vid=[0x17EF],
        pid=[
            0x6182,  # XINPUT
            0x6183,  # DINPUT
            0x6184,  # Dual DINPUT
            0x6185,  # FPS
        ],
        name=["  Legion Controller for Windows  Keyboard"]
        # report_size=64,
    )

    m = Multiplexer(
        trigger="analog_to_discrete",
        dpad="analog_to_discrete",
        led="main_to_sides",
        status="both_to_main",
    )

    REPORT_FREQ_MIN = 25
    REPORT_FREQ_MAX = 450

    REPORT_DELAY_MAX = 1 / REPORT_FREQ_MIN
    REPORT_DELAY_MIN = 1 / REPORT_FREQ_MAX

    fds = []
    devs = []
    fd_to_dev = {}

    def prepare(m):
        fs = m.open()
        devs.append(m)
        fds.extend(fs)
        for f in fs:
            fd_to_dev[f] = m

    try:
        prepare(a)
        prepare(b)
        prepare(c)
        prepare(d)
        prepare(p)
        prepare(e)
        prepare(f)

        while True:
            start = time.perf_counter()
            # Add timeout to call consumers a minimum amount of times per second
            r, _, _ = select.select(fds, [], [], REPORT_DELAY_MAX)
            evs = []
            to_run = set()
            for f in r:
                to_run.add(id(fd_to_dev[f]))

            for d in devs:
                if id(d) in to_run:
                    evs.extend(d.produce(r))

            if evs:
                evs = m.process(evs)
                # TODO: Remove. For testing
                print(evs)
                p.consume(evs)

            # If unbounded, the total number of events per second is the sum of all
            # events generated by the producers.
            # For Legion go, that would be 100 + 100 + 500 + 30 = 730
            # Since the controllers of the legion go only update at 500hz, this is
            # wasteful.
            # By setting a target refresh rate for the report and sleeping at the
            # end, we ensure that even if multiple fds become ready close to each other
            # they are combined to the same report, limiting resource use.
            # Ideally, this rate is smaller than the report rate of the hardware controller
            # to ensure there is always a report from that ready during refresh
            elapsed = time.perf_counter() - start
            if elapsed < REPORT_DELAY_MIN:
                time.sleep(REPORT_DELAY_MIN - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        for d in devs:
            d.close(True)


if __name__ == "__main__":
    controller_loop()
