# Harvest to Toggl Sync

Reads a Harvest time report CSV and creates matching time entries in Toggl.

The script groups the CSV rows by date, adds up the hours for each day, and posts **one Toggl entry
per day**. Each entry starts at 14:00 UTC and runs for the length of that day's total. Individual
Harvest rows are not preserved.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.12, which uv installs for you if it is missing
- A Toggl API token

## Setup

```bash
git clone https://github.com/michaelefisher/harvest-toggl-sync.git
cd harvest-toggl-sync
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` and builds the environment. There is no separate
activation step, because `uv run` uses that environment automatically.

Export your Toggl API token before running anything. The script reads it at import time and fails
immediately without it:

```bash
export TOGGL_API_KEY=$(op item get 5toqzhxmvgcds7ukw5qnoriahm --field 'api key' --reveal)
```

## Getting the CSV

In Harvest, run a detailed time report for the project and date range you want, then export it as
CSV. The script needs the `Date`, `Hours`, and `Cost Amount` columns. A standard Harvest detailed
export includes all three.

CSV files are gitignored, so you can keep the export in the working directory.

## Running it

Always dry run first. It prints the exact payloads and posts nothing:

```bash
uv run import.py -f timesheet.csv -p 123456789 -n "Project Name" -d
```

Then run it for real:

```bash
uv run import.py -f timesheet.csv -p 123456789 -n "Project Name"
```

### Arguments

| Flag | Required | Meaning |
| ---- | -------- | ------- |
| `-f`, `--file` | yes | Path to the Harvest CSV |
| `-p`, `--project` | yes | Toggl project id. Get this from Toggl, the script has no lookup |
| `-n`, `--name` | yes | Project name. The parser requires it, the import does not use it |
| `-w`, `--workspace` | no | Toggl workspace id. Defaults to `5534737` |
| `-d`, `--dry-run` | no | Print the payloads and post nothing |

### Reading the output

Every day prints its result, and the run ends with a reconciliation:

```
OK   2026-08-04: 5.00h
OK   2026-08-05: 4.86h
FAIL 2026-08-06: HTTP 429 ...

days processed : 18
hours in CSV   : 48.20
hours accepted : 43.20
FAILED         : 1 day(s)
```

The script exits non-zero when any day fails or when accepted hours do not match the CSV total.
Check the exit code if you run this from a script. A partial import is not supposed to look like a
successful one.

Requests are sent one per second, and 429 and 5xx responses are retried with exponential backoff,
because Toggl rate limits per API token.

## Known limits

- **Re-running duplicates entries.** There is no idempotency check. If an import fails partway,
  fix the cause and post only the missing days rather than running the whole file again.
- **Notes and tasks are discarded.** Every entry is created with the description
  `"Software development"` and `billable: true`, whatever the CSV said.
- **Start times are synthetic.** Each day starts at 14:00 UTC. A day longer than 10 hours ends
  after midnight UTC, which can move part of it into the next day in reports that use a UTC
  timezone.
- **One project per run.** All rows in the file are posted to the project given by `-p`. If the
  export covers several projects, split it first.
