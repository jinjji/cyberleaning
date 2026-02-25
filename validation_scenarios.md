# Runner Validation Scenarios

## Common setup
- Keep browser zoom at `100%`.
- Keep macOS permissions enabled for terminal/app (`Screen Recording`, `Accessibility`).
- Activate venv:
  - `.venv/bin/activate`

## Scenario A: START detection/click repeat (3 runs)
1. Open list screen where START is visible on the left side of the screen.
2. Run `python runner.py`.
3. Stop after each `[CLICK] START (...)` log and restart runner.
4. Repeat 3 times.

Expected:
- `[INIT] scale x=2.000 y=2.000` (Retina example).
- START logs contain logical coordinates, e.g. `[S0] START hit 2/2 at (x,y)`.
- No right-side false positive click.

## Scenario B: START -> S1 -> POPUP1 wait
1. Start from list screen with START visible.
2. Run `python runner.py`.
3. Confirm logs:
   - `[CLICK] START (...)`
   - `[CLICK] PLAYER(fixed) (...)` (or `PLAYER(template)`)
   - `[STATE] S1 -> S2`

Expected:
- S1 click executes once.
- State transitions to S2 without unknown state/exit.

## Scenario C: Full cycle (START -> EXIT -> back to list)
1. Run `python runner.py` and let one lecture cycle finish.
2. Confirm logs:
   - `[S2] POPUP1 -> Enter`
   - `[S3] POPUP2 -> Enter` or `[S3] POPUP2 timeout 5s -> skip to S4`
   - `[CLICK] EXIT (...)`
   - `[STATE] S4 -> S0`

Expected:
- Full cycle returns to S0.
- No hard exit on temporary START miss after scroll.

## Template quality checks
- Run `python starter_kit/capture_from_cursor.py` with mouse on real START center.
- Thresholds:
  - `same-size score >= 0.90`
  - `left-region best score >= 0.90`
- Run `python starter_kit/template_quality_check.py` and ensure LEFT quality checks are `PASS`.
