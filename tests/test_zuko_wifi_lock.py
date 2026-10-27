from contextlib import ExitStack
import importlib.util
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch


BACKEND = Path(__file__).resolve().parents[1] / "backend"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTimer:
    def __init__(self, interval, function, args=()):
        self.interval = interval
        self.function = function
        self.args = args
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        self.function(*self.args)


class ZukoLockTests(unittest.TestCase):
    def setUp(self):
        patches = ExitStack()
        self.addCleanup(patches.close)
        self.gpio = ModuleType("RPi.GPIO")
        self.gpio.BCM, self.gpio.OUT = 11, 0
        self.gpio.LOW, self.gpio.HIGH = 0, 1
        self.gpio.setmode = MagicMock()
        self.gpio.setup = MagicMock()
        self.gpio.output = MagicMock()
        rpi = ModuleType("RPi")
        rpi.GPIO = self.gpio
        self.requests = ModuleType("requests")
        self.requests.get = MagicMock(return_value=MagicMock(ok=True))
        config = ModuleType("config")
        config.UNLOCK_DOOR_GPIO = 23
        config.UNLOCK_DOOR_SECONDS = 20
        config.UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS = 2
        config.TIMESPAN_FOR_UNLOCK_ATTEMPTS = 180
        modules = {
            "RPi": rpi,
            "RPi.GPIO": self.gpio,
            "requests": self.requests,
            "config": config,
            "eventhook": load_module("eventhook", BACKEND / "eventhook.py"),
        }
        with patch.dict("sys.modules", modules):
            self.module = load_module("zuko_wifi_lock", BACKEND / "zuko_wifi_lock.py")
        self.timer_factory = patches.enter_context(
            patch.object(self.module, "Timer", side_effect=FakeTimer)
        )
        self.clock = patches.enter_context(
            patch.object(self.module, "monotonic", return_value=100)
        )
        patches.enter_context(patch.object(self.module.logging, "getLogger"))
        self.lock = self.module.ZukoLock()

    def test_only_exact_threshold_attempt_uses_http(self):
        self.lock.unlock()
        self.requests.get.assert_not_called()
        self.gpio.output.assert_called_once_with(23, self.gpio.HIGH)
        window_timer = self.lock._unlock_attempts_timer
        door_timer = self.lock._lock_timer
        self.assertEqual(window_timer.interval, 180)
        self.assertTrue(window_timer.started)

        self.clock.return_value = 110
        self.gpio.output.reset_mock()
        self.lock.unlock()
        self.requests.get.assert_called_once()
        self.gpio.output.assert_not_called()
        self.assertIs(self.lock._unlock_attempts_timer, window_timer)
        self.assertIs(self.lock._lock_timer, door_timer)
        self.assertFalse(door_timer.cancelled)

        self.lock.unlock()
        self.requests.get.assert_called_once()
        self.gpio.output.assert_called_once_with(23, self.gpio.HIGH)
        self.assertIs(self.lock._unlock_attempts_timer, window_timer)

    def test_zero_threshold_never_uses_http(self):
        self.module.UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS = 0
        for _ in range(5):
            self.lock.unlock()
        self.lock._unlock_attempts_timer.fire()
        self.lock.unlock()
        self.requests.get.assert_not_called()
        self.assertEqual(self.gpio.output.call_count, 6)

    def test_threshold_one_uses_http_on_first_attempt(self):
        self.module.UNLOCK_ATTEMPTS_UNTIL_GATE_OPENS = 1
        self.lock.unlock()
        self.requests.get.assert_called_once()
        self.gpio.output.assert_not_called()

    def test_expiry_resets_counter_and_next_call_starts_window(self):
        self.lock.unlock()
        old_timer = self.lock._unlock_attempts_timer
        timer_count = self.timer_factory.call_count
        old_timer.fire()
        self.assertEqual(self.lock._unlock_attempts, 0)
        self.assertIsNone(self.lock._unlock_attempts_timer)
        self.assertEqual(self.timer_factory.call_count, timer_count)

        self.clock.return_value = 281
        self.lock.unlock()
        self.assertEqual(self.lock._unlock_attempts, 1)
        self.assertIsNot(self.lock._unlock_attempts_timer, old_timer)
        self.requests.get.assert_not_called()

    def test_deadline_is_observed_even_if_timer_callback_is_delayed(self):
        self.lock.unlock()
        old_timer = self.lock._unlock_attempts_timer
        self.clock.return_value = 280
        self.lock.unlock()
        new_timer = self.lock._unlock_attempts_timer
        self.assertTrue(old_timer.cancelled)
        self.assertEqual(self.lock._unlock_attempts, 1)
        self.requests.get.assert_not_called()

        # Simulate the old timer callback already waiting for the counter lock.
        old_timer.fire()
        self.assertEqual(self.lock._unlock_attempts, 1)
        self.assertIs(self.lock._unlock_attempts_timer, new_timer)

    def test_gate_request_does_not_extend_gpio_high_duration(self):
        self.lock.unlock()
        door_timer = self.lock._lock_timer
        self.assertEqual(door_timer.interval, 20)
        self.assertTrue(door_timer.started)

        def slow_request(*args, **kwargs):
            door_timer.fire()
            self.gpio.output.assert_called_with(23, self.gpio.LOW)
            return MagicMock(ok=True)

        self.requests.get.side_effect = slow_request
        self.lock.unlock()
        self.assertFalse(self.lock.isUnlocked())
        self.assertEqual(self.lock._unlock_attempts, 2)

    def test_request_failure_does_not_fall_back_to_gpio(self):
        self.lock.unlock()
        door_timer = self.lock._lock_timer
        self.gpio.output.reset_mock()
        self.requests.get.side_effect = OSError("Connection failed")
        self.lock.unlock()
        self.gpio.output.assert_not_called()
        self.assertIs(self.lock._lock_timer, door_timer)


if __name__ == "__main__":
    unittest.main()
