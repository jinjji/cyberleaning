import time
import json
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

import pyautogui
import pyscreeze

# 템플릿 경로
IMG_POPUP1 = "assets/IMG_POPUP1.png"
IMG_POPUP2 = "assets/IMG_POPUP2.png"
IMG_EXIT = "assets/IMG_EXIT.png"
IMG_START = "assets/IMG_START.png"
IMG_PLAYER = "assets/IMG_PLAYER.png"  # 선택: 없으면 FIXED 클릭 fallback

# 매칭 민감도
CONFIDENCE = 0.88
PLAYER_CONFIDENCE = 0.88

# START 탐색 정책
START_SEARCH_POLICY = "LEFT_ONLY"
START_PRECHECK_TRIES = 5

# 로그 정책
SIMPLE_LOG = True
DEBUG_MODE = True
DEBUG_HISTORY_SIZE = 8

# S1 클릭 전략
S1_CLICK_MODE = "FIXED"  # FIXED | TEMPLATE

# 쿨다운(초)
ENTER_COOLDOWN = 1.0
CLICK_COOLDOWN = 2.0
S3_TIMEOUT = 5.0

# 감지 안정화
REQUIRE_HITS = 2
SCAN_INTERVAL = 0.3

# 좌표(전체화면 기준)
BASE_WIDTH = 1920
BASE_HEIGHT = 1243
BASE_X = 500
BASE_Y = 500

# 스크롤 규칙
SCROLL_WAIT = 1.0

SCALE_X = 1.0
SCALE_Y = 1.0

# JSON 로깅 설정
JSON_LOG_ENABLED = True
LOG_DIR = Path("logs")
CURRENT_LOG_FILE = None
LOG_BUFFER = []


def init_json_log():
  """JSON 로그 파일 초기화"""
  global CURRENT_LOG_FILE
  if not JSON_LOG_ENABLED:
    return

  LOG_DIR.mkdir(exist_ok=True)
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  CURRENT_LOG_FILE = LOG_DIR / f"run_{timestamp}.json"
  return CURRENT_LOG_FILE


def log(msg: str, event_type: str = "log", details: dict = None):
  """콘솔에 출력하고 JSON으로도 저장"""
  print(msg)

  if not JSON_LOG_ENABLED or CURRENT_LOG_FILE is None:
    return

  log_entry = {
    "timestamp": datetime.now().isoformat(),
    "message": msg,
    "event_type": event_type,
    "details": details or {}
  }
  LOG_BUFFER.append(log_entry)

  # 100개마다 플러시
  if len(LOG_BUFFER) >= 100:
    flush_json_log()


def flush_json_log():
  """JSON 로그를 파일에 저장"""
  global LOG_BUFFER
  if not LOG_BUFFER or CURRENT_LOG_FILE is None:
    return

  try:
    with open(CURRENT_LOG_FILE, "a") as f:
      for entry in LOG_BUFFER:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    LOG_BUFFER = []
  except Exception as e:
    print(f"[ERROR] Failed to write log: {e}", file=sys.stderr)


def scaled_point():
    cur_w, cur_h = pyautogui.size()
    rx = BASE_X / BASE_WIDTH
    ry = BASE_Y / BASE_HEIGHT
    return int(cur_w * rx), int(cur_h * ry)


def detect_display_scale():
    global SCALE_X, SCALE_Y
    sw, sh = pyautogui.size()
    shot = pyautogui.screenshot()
    iw, ih = shot.size
    if sw > 0 and sh > 0:
        SCALE_X = iw / sw
        SCALE_Y = ih / sh
    else:
        SCALE_X, SCALE_Y = 1.0, 1.0
    msg = f"[INIT] scale x={SCALE_X:.3f} y={SCALE_Y:.3f} (screen={sw}x{sh}, image={iw}x{ih})"
    log(msg, event_type="init", details={
        "scale_x": SCALE_X,
        "scale_y": SCALE_Y,
        "screen_size": (sw, sh),
        "image_size": (iw, ih)
    })


def to_image_region(region):
    if region is None:
        return None
    x, y, w, h = region
    return (
        int(round(x * SCALE_X)),
        int(round(y * SCALE_Y)),
        int(round(w * SCALE_X)),
        int(round(h * SCALE_Y)),
    )


def to_logical_point(x: int, y: int):
    lx = int(round(x / SCALE_X)) if SCALE_X else x
    ly = int(round(y / SCALE_Y)) if SCALE_Y else y
    return lx, ly


def center_points(box):
    cx_img, cy_img = pyautogui.center(box)
    cx, cy = to_logical_point(int(cx_img), int(cy_img))
    return int(cx_img), int(cy_img), cx, cy


def box_to_tuple(box):
    return int(box.left), int(box.top), int(box.width), int(box.height)


def log_start_event(box, hits: int):
    _, _, cx, cy = center_points(box)
    left, top, w, h = box_to_tuple(box)
    cx_img, cy_img, cx_log, cy_log = center_points(box)
    msg = f"[S0] START hit {hits}/{REQUIRE_HITS} at ({cx_log},{cy_log})"
    log(msg, event_type="detection", details={
        "template": "START",
        "box": (left, top, w, h),
        "center_image": (cx_img, cy_img),
        "center_logical": (cx_log, cy_log),
        "hits": hits,
        "required_hits": REQUIRE_HITS
    })


def print_start_history(history):
    if not history:
        log("[DEBUG] START history empty")
        return
    log("[DEBUG] START recent detections:")
    for idx, item in enumerate(history, 1):
        log(f"  {idx}. center={item['center_logical']} box={item['box']}")


def record_start_history(history, box):
    _, _, cx, cy = center_points(box)
    history.append({"center_logical": (cx, cy), "box": box_to_tuple(box)})


def click_scaled(label: str):
    x, y = scaled_point()
    msg = f"[CLICK] {label} ({x},{y})"
    log(msg, event_type="click", details={
        "label": label,
        "position": (x, y),
        "method": "scaled"
    })
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click()


def click_center(box, label: str):
    _, _, cx, cy = center_points(box)
    msg = f"[CLICK] {label} ({cx},{cy})"
    log(msg, event_type="click", details={
        "label": label,
        "position": (cx, cy),
        "method": "center",
        "box": box_to_tuple(box)
    })
    pyautogui.moveTo(cx, cy, duration=0.15)
    pyautogui.click()


def locate(path: str, region=None, confidence: float = CONFIDENCE):
    try:
        return pyautogui.locateOnScreen(
            path, confidence=confidence, region=to_image_region(region)
        )
    except (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException):
        return None


def left_half_region():
    w, h = pyautogui.size()
    return (0, 0, w // 2, h)


def resolve_start_region():
    if START_SEARCH_POLICY == "LEFT_ONLY":
        return left_half_region()
    log(f"[WARN] unknown policy={START_SEARCH_POLICY}, fallback LEFT_ONLY")
    return left_half_region()


def main():
    init_json_log()
    pyautogui.FAILSAFE = True
    log("3초 후 runner 시작", event_type="init")
    time.sleep(3)
    detect_display_scale()

    cooldown_until = 0.0
    start_history = deque(maxlen=DEBUG_HISTORY_SIZE)
    s3_entered_at = None

    hits = {"POPUP1": 0, "POPUP2": 0, "EXIT": 0, "START": 0}
    state = "S0_LIST_WAIT_START"

    try:
        while True:
            now = time.time()
            if now < cooldown_until:
                time.sleep(SCAN_INTERVAL)
                continue

            if state == "S0_LIST_WAIT_START":
                start_region = resolve_start_region()
                box_start = None

                for attempt in range(1, START_PRECHECK_TRIES + 1):
                    box_start = locate(IMG_START, region=start_region)
                    if box_start:
                        hits["START"] += 1
                        log_start_event(box_start, hits["START"])
                        record_start_history(start_history, box_start)
                        break
                    hits["START"] = 0
                    if DEBUG_MODE and not SIMPLE_LOG:
                        log(f"[S0] precheck miss {attempt}/{START_PRECHECK_TRIES}")
                    time.sleep(SCAN_INTERVAL)

                if box_start and hits["START"] >= REQUIRE_HITS:
                    click_center(box_start, "START")
                    cooldown_until = time.time() + CLICK_COOLDOWN
                    for k in hits:
                        hits[k] = 0
                    state = "S1_PLAYER_FOCUS"
                    log("[STATE] S0 -> S1", event_type="state_transition", details={
                        "from": "S0_LIST_WAIT_START",
                        "to": "S1_PLAYER_FOCUS"
                    })
                    time.sleep(SCAN_INTERVAL)
                    continue

                if not box_start:
                    log(f"[S0] START not found -> End (after {START_PRECHECK_TRIES} checks)")
                    pyautogui.press("end")
                    time.sleep(SCROLL_WAIT)

                    box_start2 = locate(IMG_START, region=start_region)
                    if box_start2:
                        hits["START"] = 1
                        log_start_event(box_start2, hits["START"])
                        record_start_history(start_history, box_start2)
                    else:
                        log("[S0] still not found after End")
                        if DEBUG_MODE and not SIMPLE_LOG:
                            print_start_history(start_history)

            elif state == "S1_PLAYER_FOCUS":
                if S1_CLICK_MODE == "TEMPLATE":
                    box_player = locate(IMG_PLAYER, region=None, confidence=PLAYER_CONFIDENCE)
                    if box_player:
                        click_center(box_player, "PLAYER(template)")
                    else:
                        log("[S1] PLAYER template miss -> fixed click")
                        click_scaled("PLAYER(fixed)")
                else:
                    click_scaled("PLAYER(fixed)")

                cooldown_until = time.time() + CLICK_COOLDOWN
                for k in hits:
                    hits[k] = 0
                state = "S2_WATCHING_WAIT_POPUP1"
                log("[STATE] S1 -> S2", event_type="state_transition", details={
                    "from": "S1_PLAYER_FOCUS",
                    "to": "S2_WATCHING_WAIT_POPUP1"
                })

            elif state == "S2_WATCHING_WAIT_POPUP1":
                if locate(IMG_POPUP1):
                    hits["POPUP1"] += 1
                else:
                    hits["POPUP1"] = 0

                if hits["POPUP1"] >= REQUIRE_HITS:
                    log("[S2] POPUP1 -> Enter", event_type="detection", details={
                        "template": "POPUP1"
                    })
                    pyautogui.press("enter")
                    cooldown_until = time.time() + ENTER_COOLDOWN
                    for k in hits:
                        hits[k] = 0
                    state = "S3_WAIT_POPUP2"
                    s3_entered_at = time.time()
                    log("[STATE] S2 -> S3", event_type="state_transition", details={
                        "from": "S2_WATCHING_WAIT_POPUP1",
                        "to": "S3_WAIT_POPUP2"
                    })

            elif state == "S3_WAIT_POPUP2":
                if locate(IMG_POPUP2):
                    hits["POPUP2"] += 1
                else:
                    hits["POPUP2"] = 0

                if hits["POPUP2"] >= REQUIRE_HITS:
                    log("[S3] POPUP2 -> Enter", event_type="detection", details={
                        "template": "POPUP2"
                    })
                    pyautogui.press("enter")
                    cooldown_until = time.time() + ENTER_COOLDOWN
                    for k in hits:
                        hits[k] = 0
                    state = "S4_WAIT_EXIT"
                    s3_entered_at = None
                    log("[STATE] S3 -> S4", event_type="state_transition", details={
                        "from": "S3_WAIT_POPUP2",
                        "to": "S4_WAIT_EXIT"
                    })
                elif s3_entered_at and (time.time() - s3_entered_at) >= S3_TIMEOUT:
                    msg = f"[S3] POPUP2 timeout {S3_TIMEOUT:.0f}s -> skip to S4"
                    log(msg, event_type="timeout", details={
                        "timeout_duration": S3_TIMEOUT,
                        "elapsed": time.time() - s3_entered_at
                    })
                    hits["POPUP2"] = 0
                    state = "S4_WAIT_EXIT"
                    s3_entered_at = None
                    log("[STATE] S3 -> S4 (skip)", event_type="state_transition", details={
                        "from": "S3_WAIT_POPUP2",
                        "to": "S4_WAIT_EXIT",
                        "reason": "timeout"
                    })

            elif state == "S4_WAIT_EXIT":
                box_exit = locate(IMG_EXIT)
                if box_exit:
                    hits["EXIT"] += 1
                else:
                    hits["EXIT"] = 0

                if hits["EXIT"] >= REQUIRE_HITS:
                    click_center(box_exit, "EXIT")
                    cooldown_until = time.time() + CLICK_COOLDOWN
                    click_scaled("LIST_FOCUS")
                    cooldown_until = time.time() + CLICK_COOLDOWN
                    for k in hits:
                        hits[k] = 0
                    state = "S0_LIST_WAIT_START"
                    log("[STATE] S4 -> S0", event_type="state_transition", details={
                        "from": "S4_WAIT_EXIT",
                        "to": "S0_LIST_WAIT_START"
                    })

            else:
                log(f"[ERROR] Unknown state: {state}")
                return

            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        log("\nStopped (Ctrl+C)", event_type="shutdown")
        flush_json_log()
    finally:
        flush_json_log()
        if CURRENT_LOG_FILE and JSON_LOG_ENABLED:
            print(f"\n[LOG] JSON log saved to: {CURRENT_LOG_FILE}")


if __name__ == "__main__":
    main()
