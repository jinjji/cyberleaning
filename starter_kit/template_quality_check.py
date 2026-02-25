import time

import cv2
import numpy as np
import pyautogui
import pyscreeze
from PIL import Image

IMG_START = "assets/IMG_START.png"
CONFIDENCE_LEVELS = [0.96, 0.93, 0.90, 0.88, 0.85]
QUALITY_THRESHOLD = 0.90


def left_half_region():
    w, h = pyautogui.size()
    return (0, 0, w // 2, h)


def locate_all(path: str, confidence: float, region=None):
    try:
        return list(pyautogui.locateAllOnScreen(path, confidence=confidence, region=region))
    except (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException):
        return []


def main():
    print("3초 후 시작")
    time.sleep(3)

    screen = pyautogui.size()
    region_left = left_half_region()
    template = Image.open(IMG_START)
    print("screen:", screen)
    print("left_region:", region_left)
    print("template:", template.size, template.mode)

    left_match_090 = False
    for conf in CONFIDENCE_LEVELS:
        full_boxes = locate_all(IMG_START, confidence=conf, region=None)
        left_boxes = locate_all(IMG_START, confidence=conf, region=region_left)
        print(f"conf={conf} full={len(full_boxes)} left={len(left_boxes)}")
        if conf >= 0.90 and left_boxes:
            left_match_090 = True

    screenshot = pyautogui.screenshot()
    screen_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    tpl_rgba = cv2.imread(IMG_START, cv2.IMREAD_UNCHANGED)
    template_bgr = tpl_rgba[:, :, :3]

    full_res = cv2.matchTemplate(screen_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    _, full_max, _, full_loc = cv2.minMaxLoc(full_res)

    x, y, w, h = region_left
    left_img = screen_bgr[y:y + h, x:x + w]
    left_res = cv2.matchTemplate(left_img, template_bgr, cv2.TM_CCOEFF_NORMED)
    _, left_max, _, left_loc = cv2.minMaxLoc(left_res)
    left_loc_abs = (left_loc[0] + x, left_loc[1] + y)

    print("FULL best:", f"{full_max:.4f}", full_loc)
    print("LEFT best:", f"{left_max:.4f}", left_loc_abs)
    print("PASS left_score:", left_max >= QUALITY_THRESHOLD)
    print("PASS left_conf>=0.90:", left_match_090)


if __name__ == "__main__":
    main()
