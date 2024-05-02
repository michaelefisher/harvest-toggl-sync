import csv
import itertools
import os
from base64 import b64encode
from datetime import datetime
from typing import Dict, List

import requests


PROJECT_ID: int = 201698919
PROJECT_NAME: str = "Reach Backend Support"
WORKSPACE_ID: int = 5534737

toggl_api_key: bytes = f"{os.environ['TOGGL_API_KEY']}:api_token".encode()


# Function to add hours for each day
def add_hours_for_day(rows):
    total_hours: float = 0.00
    total_cost_amount: float = 0.00
    last_row_per_date = {}

    for data in rows:
        # Convert Hours and Cost Amount to float
        hours = float(data["Hours"])
        cost_amount = float(data["Cost Amount"])

        # Add hours and cost amount to the totals
        total_hours += hours
        total_cost_amount += cost_amount

        # Update the dictionary
        data["Total Hours"] = total_hours * 3600
        data["Total Cost Amount"] = total_cost_amount

        # Store this row as the last row for this date
        last_row_per_date[data["Date"]] = data

    # Yield only the last row for each date
    for row in last_row_per_date.values():
        yield row


def parse_date(date: str) -> List[int]:
    return [int(x) for x in date.split("-")]


def format_datetime(date: str) -> str:
    date = datetime(
        year=parse_date(date)[0],
        month=parse_date(date)[1],
        day=parse_date(date)[2],
        hour=14,
        minute=0,
        second=0,
    )
    return datetime.strftime(date, "%Y-%m-%dT%H:%M:%SZ")


def group_by_date(sorted_rows):
    # Group the sorted rows by date
    grouped_rows = itertools.groupby(sorted_rows, key=lambda row: row["Date"])

    # Yield each group one at a time
    for date, rows in grouped_rows:
        yield date, list(rows)


modified_data: List[Dict[bytes, bytes]] = []

with open("fixtures/ingest/data.csv", "r") as file:
    reader = csv.DictReader(file)
    next(reader)

    # Sort and group the rows by the first column - Date
    sorted_rows = sorted(reader, key=lambda row: row["Date"])

    for date, rows in group_by_date(sorted_rows):
        for updated_data in add_hours_for_day(rows):
            modified_data.append(updated_data)

print("Modified data: ", modified_data)

for row in modified_data:
    data = requests.post(
        f"https://api.track.toggl.com/api/v9/workspaces/{WORKSPACE_ID}/time_entries?meta=true",
        json={
            "billable": True,
            "created_with": "python-toggl",
            "description": "Software development",
            "duration": int(row["Total Hours"]),
            "project_id": PROJECT_ID,
            "start": format_datetime(row["Date"]),
            "wid": WORKSPACE_ID,
            "workspace_id": WORKSPACE_ID,
        },
        headers={
            "content-type": "application/json",
            "Authorization": "Basic %s" % b64encode(toggl_api_key).decode("ascii"),
        },
    )
    print(data.json())
