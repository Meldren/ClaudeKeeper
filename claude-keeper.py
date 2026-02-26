#!/usr/bin/env python3
import subprocess, sys, os
from datetime import datetime
from pathlib import Path

# ——— Config ———
START_TIME = "10:00"
WINDOWS = 4
TIMEZONE = "Europe/Moscow"
COMMAND = 'claude -p "hello"'
# ——————————————

SERVICE = "claude-session"
SCRIPT = Path(__file__).resolve()
LOG = SCRIPT.with_name("claude-keeper.log")


def now_tz():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(TIMEZONE))


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"[{now_tz():%d.%m %H:%M:%S}] {msg}\n")


def schedule_times():
    h, m = map(int, START_TIME.split(":"))
    return [((h + i * 5) % 24, m) for i in range(WINDOWS)]


def install():
    if os.geteuid() != 0:
        sys.exit("Run with sudo")

    user = os.environ.get("SUDO_USER", os.environ["USER"])
    times = schedule_times()
    tz = f" {TIMEZONE}" if TIMEZONE else ""
    cal = "\n".join(f"OnCalendar=*-*-* {h:02d}:{m:02d}:00{tz}" for h, m in times)

    print("Schedule:")
    for h, m in times:
        print(f"  {h:02d}:{m:02d}")

    Path(f"/etc/systemd/system/{SERVICE}.service").write_text(
        f"[Unit]\nDescription=Claude session refresh\n"
        f"[Service]\nType=oneshot\nUser={user}\n"
        f"ExecStart=/usr/bin/env python3 {SCRIPT}\n"
    )

    Path(f"/etc/systemd/system/{SERVICE}.timer").write_text(
        f"[Unit]\nDescription=Claude session refresh timer\n"
        f"[Timer]\n{cal}\nPersistent=true\n"
        f"[Install]\nWantedBy=timers.target\n"
    )

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", f"{SERVICE}.timer"], check=True)
    print(f"Done! Use: python3 {SCRIPT.name} status")


def uninstall():
    if os.geteuid() != 0:
        sys.exit("Run with sudo")
    subprocess.run(["systemctl", "stop", f"{SERVICE}.timer"], stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "disable", f"{SERVICE}.timer"], stderr=subprocess.DEVNULL)
    for ext in ("service", "timer"):
        Path(f"/etc/systemd/system/{SERVICE}.{ext}").unlink(missing_ok=True)
    subprocess.run(["systemctl", "daemon-reload"])
    print("Removed.")


def status():
    r = subprocess.run(
        ["systemctl", "show", f"{SERVICE}.timer", "--property=NextElapseUSecRealtime"],
        capture_output=True, text=True
    )
    val = r.stdout.strip().split("=", 1)[-1].strip()
    if val:
        from zoneinfo import ZoneInfo
        utc_dt = datetime.strptime(val, "%a %Y-%m-%d %H:%M:%S %Z").replace(tzinfo=ZoneInfo("UTC"))
        local_dt = utc_dt.astimezone(ZoneInfo(TIMEZONE))
        left = local_dt - datetime.now(ZoneInfo(TIMEZONE))
        hours, remainder = divmod(int(left.total_seconds()), 3600)
        minutes = remainder // 60
        print(f"Next run: {local_dt:%d.%m %H:%M} ({hours}h {minutes}m left)")
    else:
        print("Timer not installed")

    print()
    if not LOG.exists():
        print("No logs yet")
        return

    import re
    runs, current = [], {}
    for line in LOG.read_text().splitlines():
        m = re.match(r"\[(.+?)] (.+)", line)
        if not m:
            continue
        ts, msg = m.groups()
        if msg == "Session refresh started":
            current = {"time": ts}
        elif msg.startswith("Output:"):
            current["output"] = msg[8:]
        elif msg.startswith("OK") or msg.startswith("FAILED"):
            current["result"] = msg
            runs.append(current)
            current = {}

    if not runs:
        print("No completed runs yet")
        return

    print(f"{'Time':<16} {'Result':<18} {'Details'}")
    print(f"{'─' * 16} {'─' * 18} {'─' * 40}")
    for r in runs[-10:]:
        marker = "+" if r.get("result", "").startswith("OK") else "-"
        print(f"{r.get('time', '?'):<16} [{marker}] {r.get('result', '?'):<14} {r.get('output', '')}")


def run():
    log("Session refresh started")
    start = datetime.now()
    r = subprocess.run(COMMAND, shell=True, capture_output=True, text=True)
    elapsed = (datetime.now() - start).total_seconds()

    output = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
    if output:
        log(f"Output: {output}")

    if r.returncode == 0:
        log(f"OK ({elapsed:.1f}s)")
    else:
        log(f"FAILED ({elapsed:.1f}s)")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "run"
    def test():
        run()
        status()

    {"install": install, "uninstall": uninstall, "status": status, "test": test}.get(action, run)()
