# Harvest to Toggl Sync

This script is used to sync time entries from Harvest to Toggl.

## Installation

1. Clone the repository
2. Install the dependencies with `pip install -r requirements.txt`
3. Ensure you've exported `TOGGL_API_KEY` to your environment:
```bash
export TOGGL_API_KEY=$(op item get 5toqzhxmvgcds7ukw5qnoriahm --field 'api key' --reveal)

```

Additionally, you'll need to download the individual daily time entries from harvest as a CSV file.
