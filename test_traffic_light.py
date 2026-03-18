import unittest

from traffic_light import TrafficDurations, TrafficLightController, TrafficState


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TrafficLightControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.controller = TrafficLightController(
            durations=TrafficDurations(
                green_seconds=10.0,
                yellow_seconds=3.0,
                red_seconds=5.0,
                pedestrian_red_seconds=7.0,
            ),
            now_func=self.clock.monotonic,
            debounce_seconds=0.1,
        )

    def test_initial_state_is_green(self) -> None:
        self.assertEqual(self.controller.current_state, TrafficState.GREEN)
        outputs = self.controller.get_outputs()
        self.assertTrue(outputs["car_green"])
        self.assertFalse(outputs["car_yellow"])
        self.assertFalse(outputs["car_red"])

    def test_basic_cycle_green_to_yellow_to_red_to_green(self) -> None:
        self.clock.advance(10.0)
        self.controller.update()
        self.assertEqual(self.controller.current_state, TrafficState.YELLOW)

        self.clock.advance(3.0)
        self.controller.update()
        self.assertEqual(self.controller.current_state, TrafficState.RED)

        self.clock.advance(5.0)
        self.controller.update()
        self.assertEqual(self.controller.current_state, TrafficState.GREEN)

    def test_pedestrian_request_is_stored(self) -> None:
        accepted = self.controller.request_pedestrian_crossing()
        self.assertTrue(accepted)
        self.assertTrue(self.controller.pedestrian_request)

    def test_duplicate_button_press_is_ignored_when_request_exists(self) -> None:
        first = self.controller.request_pedestrian_crossing()
        self.clock.advance(0.2)
        second = self.controller.request_pedestrian_crossing()

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(self.controller.pedestrian_request)

    def test_debouncing_blocks_rapid_repeat_press(self) -> None:
        first = self.controller.request_pedestrian_crossing()
        self.clock.advance(0.05)
        second = self.controller.request_pedestrian_crossing()

        self.assertTrue(first)
        self.assertFalse(second)

    def test_pedestrian_request_is_processed_on_next_red(self) -> None:
        self.controller.request_pedestrian_crossing()

        self.clock.advance(10.0)
        self.controller.update()
        self.assertEqual(self.controller.current_state, TrafficState.YELLOW)

        self.clock.advance(3.0)
        self.controller.update()
        self.assertEqual(self.controller.current_state, TrafficState.RED)
        self.assertTrue(self.controller.pedestrian_crossing_active)
        self.assertFalse(self.controller.pedestrian_request)

        outputs = self.controller.get_outputs()
        self.assertTrue(outputs["car_red"])
        self.assertTrue(outputs["pedestrian_go"])

    def test_after_pedestrian_red_returns_to_green(self) -> None:
        self.controller.request_pedestrian_crossing()

        self.clock.advance(10.0)
        self.controller.update()

        self.clock.advance(3.0)
        self.controller.update()

        self.clock.advance(7.0)
        self.controller.update()

        self.assertEqual(self.controller.current_state, TrafficState.GREEN)
        self.assertFalse(self.controller.pedestrian_crossing_active)

    def test_only_one_car_led_is_active(self) -> None:
        for state in (TrafficState.GREEN, TrafficState.YELLOW, TrafficState.RED):
            self.controller.current_state = state
            outputs = self.controller.get_outputs()
            active_car_leds = sum(
                1 for key in ("car_green", "car_yellow", "car_red") if outputs[key]
            )
            self.assertEqual(active_car_leds, 1)


if __name__ == "__main__":
    unittest.main()