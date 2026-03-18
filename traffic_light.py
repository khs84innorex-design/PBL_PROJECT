from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, Optional


class TrafficState(Enum):
    GREEN = auto()
    YELLOW = auto()
    RED = auto()


@dataclass(frozen=True)
class TrafficDurations:
    green_seconds: float = 10.0
    yellow_seconds: float = 3.0
    red_seconds: float = 5.0
    pedestrian_red_seconds: float = 7.0


class TrafficLightController:
    """
    스마트 신호등 상태 머신.
    - 기본 순환: GREEN -> YELLOW -> RED -> GREEN
    - 보행자 요청은 GREEN/YELLOW 중 등록 가능
    - 요청이 있으면 다음 RED 구간에서 보행 가능 상태를 제공
    - 버튼 연타는 디바운싱 + 중복 요청 방지로 1회 처리
    """

    def __init__(
        self,
        durations: TrafficDurations,
        now_func: Callable[[], float],
        debounce_seconds: float = 0.1,
    ) -> None:
        self.durations = durations
        self.now_func = now_func
        self.debounce_seconds = debounce_seconds

        self.current_state: TrafficState = TrafficState.GREEN
        self.state_started_at: float = self.now_func()

        self.pedestrian_request: bool = False
        self.pedestrian_crossing_active: bool = False
        self.last_button_press_at: Optional[float] = None

    def request_pedestrian_crossing(self, pressed_at: Optional[float] = None) -> bool:
        """
        보행자 요청 등록.
        반환값:
        - True: 새 요청이 정상 등록됨
        - False: 디바운싱 또는 이미 요청 등록 상태라 무시됨
        """
        now = self.now_func() if pressed_at is None else pressed_at

        if self.last_button_press_at is not None:
            if (now - self.last_button_press_at) < self.debounce_seconds:
                return False

        self.last_button_press_at = now

        if self.pedestrian_request:
            return False

        # RED 중에는 이미 처리 구간이거나 곧 처리 중이므로 새 요청은 다음 사이클용으로 보관 가능.
        # Toy Project 기준으로 단순하게 1회 요청 플래그만 유지한다.
        self.pedestrian_request = True
        return True

    def update(self, now: Optional[float] = None) -> bool:
        """
        loop에서 반복 호출.
        상태가 바뀌면 True, 유지되면 False 반환.
        """
        current_time = self.now_func() if now is None else now
        elapsed = current_time - self.state_started_at

        target_duration = self._current_state_duration()

        if elapsed < target_duration:
            return False

        self._transition_to_next_state(current_time)
        return True

    def _current_state_duration(self) -> float:
        if self.current_state is TrafficState.GREEN:
            return self.durations.green_seconds
        if self.current_state is TrafficState.YELLOW:
            return self.durations.yellow_seconds

        # RED
        if self.pedestrian_crossing_active:
            return self.durations.pedestrian_red_seconds
        return self.durations.red_seconds

    def _transition_to_next_state(self, now: float) -> None:
        if self.current_state is TrafficState.GREEN:
            self._enter_state(TrafficState.YELLOW, now)
            return

        if self.current_state is TrafficState.YELLOW:
            self._enter_state(TrafficState.RED, now)
            return

        if self.current_state is TrafficState.RED:
            self._enter_state(TrafficState.GREEN, now)
            return

        raise RuntimeError(f"Unknown state: {self.current_state}")

    def _enter_state(self, next_state: TrafficState, now: float) -> None:
        self.current_state = next_state
        self.state_started_at = now

        if next_state is TrafficState.RED:
            if self.pedestrian_request:
                self.pedestrian_crossing_active = True
                self.pedestrian_request = False
            else:
                self.pedestrian_crossing_active = False
            return

        if next_state is TrafficState.GREEN:
            self.pedestrian_crossing_active = False
            return

        if next_state is TrafficState.YELLOW:
            self.pedestrian_crossing_active = False
            return

    def get_outputs(self) -> Dict[str, bool]:
        """
        실제 LED/GPIO에 연결하기 위한 출력 상태.
        동시에 잘못된 LED 조합이 켜지지 않도록 1개만 True.
        """
        return {
            "car_green": self.current_state is TrafficState.GREEN,
            "car_yellow": self.current_state is TrafficState.YELLOW,
            "car_red": self.current_state is TrafficState.RED,
            "pedestrian_go": self.current_state is TrafficState.RED and self.pedestrian_crossing_active,
            "pedestrian_wait": self.current_state is not TrafficState.RED or not self.pedestrian_crossing_active,
        }

    def snapshot(self) -> Dict[str, object]:
        return {
            "state": self.current_state.name,
            "pedestrian_request": self.pedestrian_request,
            "pedestrian_crossing_active": self.pedestrian_crossing_active,
            "outputs": self.get_outputs(),
        }