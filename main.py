import time
import threading

from traffic_light import TrafficDurations, TrafficLightController


def format_outputs(outputs: dict) -> str:
    active = [name for name, on in outputs.items() if on]
    return ", ".join(active) if active else "none"


def input_thread(controller: TrafficLightController):
    """
    별도 스레드에서 사용자 입력 처리
    """
    while True:
        user_input = input().strip().lower()

        if user_input == "p":
            accepted = controller.request_pedestrian_crossing()
            if accepted:
                print("[BUTTON] 보행자 요청 등록")
            else:
                print("[BUTTON] 무시됨 (중복/디바운싱)")

        elif user_input == "q":
            print("종료합니다.")
            exit(0)


def main():
    controller = TrafficLightController(
        durations=TrafficDurations(
            green_seconds=5,
            yellow_seconds=2,
            red_seconds=3,
            pedestrian_red_seconds=5,
        ),
        now_func=time.monotonic,
        debounce_seconds=0.15,
    )

    print("=== 스마트 신호등 시뮬레이터 ===")
    print("p: 보행자 버튼 | q: 종료\n")

    # 입력 스레드 시작
    thread = threading.Thread(target=input_thread, args=(controller,), daemon=True)
    thread.start()

    last_state = None

    while True:
        changed = controller.update()

        snapshot = controller.snapshot()
        state = snapshot["state"]

        # 상태 바뀔 때만 출력
        if changed or state != last_state:
            print(f"[STATE] {state} | {format_outputs(snapshot['outputs'])}")
            last_state = state

        time.sleep(0.1)


if __name__ == "__main__":
    main()