# ClaudeKeeper

Single-file systemd scheduler that auto-refreshes Claude Code session windows on Linux.

## Setup

1. Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and log in
2. Edit config at the top of `claude-keeper.py`:

```python
START_TIME = "10:00"           # First window (24h format)
WINDOWS = 4                    # Sessions count (5h apart)
TIMEZONE = "Europe/Moscow"     # Your timezone
COMMAND = 'claude -p "hello"'  # Command to run
```

3. Install and forget:

```bash
sudo python3 claude-keeper.py install
```

## Commands

```bash
sudo python3 claude-keeper.py install    # create & start systemd timer
sudo python3 claude-keeper.py uninstall  # remove timer
python3 claude-keeper.py status          # show schedule & recent logs
python3 claude-keeper.py test            # run refresh once to verify setup
```

## How it works

Creates a systemd timer that runs `claude -p "hello"` at each scheduled time, refreshing the 5-hour session window. Logs are written to `claude-keeper.log` next to the script.
