"""Quick end-to-end validation for RememberWindowsState."""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')

failures = []

def check(name, condition, detail=''):
    mark = 'OK ' if condition else 'FAIL'
    print(f'[{mark}] {name}' + (f' — {detail}' if detail else ''))
    if not condition:
        failures.append(name)

# ── Config ────────────────────────────────────────────────────────────────────
from config import Config
cfg = Config()
original = cfg.interval
cfg.interval = 99
check('Config write', cfg.interval == 99)
cfg.interval = original
check('Config restore', cfg.interval == original)

# ── Window tracker ────────────────────────────────────────────────────────────
from window_tracker import get_open_windows, save_snapshot, load_snapshot
wins = get_open_windows()
check('Window enumeration', len(wins) > 0, f'{len(wins)} windows')
print('  Detected:')
for w in wins:
    print(f'    {w["exe_name"]:28s} {w["title"][:45]}')

save_snapshot(wins, cfg.state_file)
loaded = load_snapshot(cfg.state_file)
check('Snapshot save/load', loaded and len(loaded['windows']) == len(wins))

# ── Restorer ──────────────────────────────────────────────────────────────────
from window_restorer import filter_not_open
not_open = filter_not_open(wins)
check('filter_not_open (all running)', len(not_open) == 0, f'got {len(not_open)}')

# ── Scheduler ─────────────────────────────────────────────────────────────────
from scheduler import WindowScheduler
ticks = []
sch = WindowScheduler(callback=lambda: ticks.append(1), interval=1)
sch.start()
time.sleep(2.3)
sch.stop()
check('Scheduler ticks', len(ticks) >= 2, f'{len(ticks)} ticks in 2.3s')

# ── Startup registry ──────────────────────────────────────────────────────────
from startup import enable_startup, disable_startup, is_startup_enabled
enable_startup()
check('Enable startup', is_startup_enabled())
disable_startup()
check('Disable startup', not is_startup_enabled())

# ── Summary ───────────────────────────────────────────────────────────────────
print()
if failures:
    print(f'FAILED: {failures}')
    sys.exit(1)
else:
    print('=== ALL TESTS PASSED ===')
