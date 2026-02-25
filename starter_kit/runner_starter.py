import time
from collections import deque

import pyautogui
import pyscreeze

try:
    import config as cfg
except ImportError:
    import config_example as cfg

SCALE_X = 1.0
SCALE_Y = 1.0


def log(msg: str):
    print(msg)


def scaled_point():
    cur_w, cur_h = pyautogui.size()
    rx = cfg.BASE_X / cfg.BASE_WIDTH
    ry = cfg.BASE_Y / cfg.BASE_HEIGHT
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
    log(f"[INIT] scale x={SCALE_X:.3f} y={SCALE_Y:.3f}")


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


def center_logical(box):
    cx_img, cy_img = pyautogui.center(box)
    return to_logical_point(int(cx_img), int(cy_img))


def click_scaled(label: str):
    x, y = scaled_point()
    log(f"[CLICK] {label} ({x},{y})")
    pyautogui.moveTo(x, y, duration=0.15)
    pyautogui.click()


def click_center(box, label: str):
    cx, cy = center_logical(box)
    log(f"[CLICK] {label} ({cx},{cy})")
    pyautogui.moveTo(cx, cy, duration=0.15)
    pyautogui.click()


def locate(path: str, region=None, confidence=None):
    conf = cfg.CONFIDENCE if confidence is None else confidence
    try:
        return pyautogui.locateOnScreen(path, confidence=conf, region=to_image_region(region))
    except (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException):
        return None


def left_half_region():
    w, h = pyautogui.size()
    return (0, 0, w // 2, h)


def resolve_start_region():
    if cfg.START_SEARCH_POLICY == "LEFT_ONLY":
        return left_half_region()
    return left_half_region()


def main():
    pyautogui.FAILSAFE = True
    log("3초 후 시작")
    time.sleep(3)
    detect_display_scale()

    hits = {"START": 0, "POPUP1": 0, "POPUP2": 0, "EXIT": 0}
    state = "S0"
    cooldown_until = 0.0
    s3_entered_at = None
    history = deque(maxlen=cfg.DEBUG_HISTORY_SIZE)

    while True:
        now = time.time()
        if now < cooldown_until:
            time.sleep(cfg.SCAN_INTERVAL)
            continue

        if state == "S0":
            start_region = resolve_start_region()
            box_start = None
            for _ in range(cfg.START_PRECHECK_TRIES):
                box_start = locate(cfg.IMG_START, region=start_region)
                if box_start:
                    hits["START"] += 1
                    cx, cy = center_logical(box_start)
                    history.append((cx, cy))
                    log(f"[S0] START {hits['START']}/{cfg.REQUIRE_HITS} at ({cx},{cy})")
                    break
                hits["START"] = 0
                time.sleep(cfg.SCAN_INTERVAL)

            if box_start and hits["START"] >= cfg.REQUIRE_HITS:
                click_center(box_start, "START")
                for k in hits:
                    hits[k] = 0
                cooldown_until = time.time() + cfg.CLICK_COOLDOWN
                state = "S1"
                log("[STATE] S0 -> S1")
                continue

            if not box_start:
                log("[S0] START miss -> End")
                pyautogui.press("end")
                time.sleep(1.0)

        elif state == "S1":
            if cfg.S1_CLICK_MODE == "TEMPLATE":
                box_player = locate(cfg.IMG_PLAYER, confidence=cfg.PLAYER_CONFIDENCE)
                if box_player:
                    click_center(box_player, "PLAYER(template)")
                else:
                    click_scaled("PLAYER(fixed)")
            else:
                click_scaled("PLAYER(fixed)")

            cooldown_until = time.time() + cfg.CLICK_COOLDOWN
            state = "S2"
            log("[STATE] S1 -> S2")

        elif state == "S2":
            if locate(cfg.IMG_POPUP1):
                hits["POPUP1"] += 1
            else:
                hits["POPUP1"] = 0

            if hits["POPUP1"] >= cfg.REQUIRE_HITS:
                pyautogui.press("enter")
                for k in hits:
                    hits[k] = 0
                cooldown_until = time.time() + cfg.ENTER_COOLDOWN
                s3_entered_at = time.time()
                state = "S3"
                log("[STATE] S2 -> S3")

        elif state == "S3":
            if locate(cfg.IMG_POPUP2):
                hits["POPUP2"] += 1
            else:
                hits["POPUP2"] = 0

            if hits["POPUP2"] >= cfg.REQUIRE_HITS:
                pyautogui.press("enter")
                cooldown_until = time.time() + cfg.ENTER_COOLDOWN
                for k in hits:
                    hits[k] = 0
                state = "S4"
                log("[STATE] S3 -> S4")
            elif s3_entered_at and (time.time() - s3_entered_at) >= cfg.S3_TIMEOUT:
                log(f"[S3] timeout {cfg.S3_TIMEOUT:.0f}s -> skip S4")
                state = "S4"

        elif state == "S4":
            box_exit = locate(cfg.IMG_EXIT)
            if box_exit:
                hits["EXIT"] += 1
            else:
                hits["EXIT"] = 0

            if hits["EXIT"] >= cfg.REQUIRE_HITS:
                click_center(box_exit, "EXIT")
                click_scaled("LIST_FOCUS")
                cooldown_until = time.time() + cfg.CLICK_COOLDOWN
                for k in hits:
                    hits[k] = 0
                state = "S0"
                log("[STATE] S4 -> S0")

        time.sleep(cfg.SCAN_INTERVAL)


if __name__ == "__main__":
    main()
