from threading import Event, Thread
from typing import Any, Sequence

from hhd.plugins import (
    Config,
    Context,
    HHDPlugin,
    HHDPluginInfo,
    get_relative_fn,
    Emitter,
)


class LegionControllersPlugin(HHDPlugin):
    def open(
        self,
        conf: Config,
        emit: Emitter,
        context: Context,
    ):
        from .base import plugin_run

        self.event = Event()
        self.t = Thread(target=plugin_run, args=(self.cfg, context, self.event))
        self.t.start()

    def close(self):
        self.event.set()
        self.t.join()


def autodetect(existing: Sequence[HHDPlugin]) -> Sequence[HHDPluginInfo]:
    if len(existing):
        return []

    # Match just product number, should be enough for now
    with open("/sys/devices/virtual/dmi/id/product_name") as f:
        if not f.read().strip() == "83E1":
            return []

    return [
        {
            "name": "legion_go_controllers",
            "plugin": LegionControllersPlugin(),
            "priority": 18,
            "config": get_relative_fn("config.yaml"),
            "version": 3,
        }
    ]


def main():
    from .base import main

    main(False)


if __name__ == "__main__":
    main()
