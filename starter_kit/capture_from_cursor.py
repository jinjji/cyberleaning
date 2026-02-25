import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

IMG_START = "assets/IMG_START.png"
OUT_DIR = Path("assets")


def clamp(v: int, low: int, high: int) -> int:
    return max(low, min(v, high))


def main():
    template_rgba = cv2.imread(IMG_START, cv2.IMREAD_UNCHANGED)
    if template_rgba is None:
        print(f"template load failed: {IMG_START}")
        return

    template = template_rgba[:, :, :3]
    th, tw = template.shape[:2]
    sw, sh = pyautogui.size()

    print("마우스를 실제 START 버튼 중앙에 올리고 Enter")
    input("> ")
    time.sleep(0.1)

    cx, cy = map(int, pyautogui.position())
    left = clamp(cx - tw // 2, 0, sw - tw)
    top = clamp(cy - th // 2, 0, sh - th)
    patch_img = pyautogui.screenshot(region=(left, top, tw, th))
    patch_bgr = cv2.cvtColor(np.array(patch_img), cv2.COLOR_RGB2BGR)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidate = OUT_DIR / "IMG_START_candidate.png"
    cv2.imwrite(str(candidate), patch_bgr)
    print(f"saved: {candidate}")
    print("필요하면 IMG_START.png로 교체하세요.")


if __name__ == "__main__":
    main()
