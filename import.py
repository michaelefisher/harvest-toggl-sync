#!/usr/bin/env python3

import argparse
import csv
import json
import itertools
import os
import math
import sys
import time
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Dict, List

import requests

WORKSPACE_ID: int = 5534737

toggl_api_key: bytes = f"{os.environ['TOGGL_API_KEY']}:api_token".encode()

# Function to add hours for each day
def add_hours_for_day(rows):
    total_hours: int = 0
    total_cost_amount: float = 0.00
    last_row_per_date = {}

    for data in rows:
        # Convert Hours and Cost Amount to float
        hours = float(data["Hours"])
        cost_amount = float(data["Cost Amount"])

        # Convert hours (1.5) to seconds
        hours = hours * 3600

        # Add hours and cost amount to the totals
        total_hours += hours
        total_cost_amount += cost_amount

        # Update the dictionary
        data["Duration"] = total_hours
        # Use datetime to add the total_hours to start time
        data['End Date'] = datetime.strptime(format_datetime(data['Date']), "%Y-%m-%dT%H:%M:%SZ") + timedelta(seconds=total_hours)
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


def read_file(file_path: str, project_id: int, project_name: str, workspace_id: int = WORKSPACE_ID, dry_run: bool = False):
    modified_data: List[Dict[str, str]] = []

    csv_total_hours: float = 0.0

    with open(file_path, "r") as file:
        reader = csv.DictReader(file)

        # Sort and group the rows by the first column - Date
        sorted_rows = sorted(reader, key=lambda row: row["Date"])
        csv_total_hours = sum(float(row["Hours"]) for row in sorted_rows)

        for date, rows in group_by_date(sorted_rows):
            for updated_data in add_hours_for_day(rows):
                modified_data.append(updated_data)

    dry_run_list = []
    posted_seconds = 0.0
    failures = []

    for row in modified_data:
        payload={
                "billable": True,
                "created_with": "python-toggl",
                "description": "Software development",
                "project_id": project_id,
                "start": format_datetime(row["Date"]),
                # "start_date": format_datetime(row["Date"]),
                "stop": datetime.strftime(row["End Date"], "%Y-%m-%dT%H:%M:%SZ"),
                "wid": workspace_id,
                "workspace_id": workspace_id,
        }

        # A zero-length day produces start == stop, which Toggl rejects.
        if row["Duration"] <= 0:
            print(f"SKIP {row['Date']}: duration is 0")
            continue

        if dry_run:
            dry_run_list.append(payload)
            posted_seconds += row["Duration"]
            continue

        # Toggl rate limits per token. Retry on 429 and 5xx instead of
        # dropping the entry silently.
        for attempt in range(5):
            response = requests.post(
                f"https://api.track.toggl.com/api/v9/workspaces/{workspace_id}/time_entries?meta=true",
                json=payload,
                headers={
                    "content-type": "application/json",
                    "Authorization": "Basic %s" % b64encode(toggl_api_key).decode("ascii"),
                },
            )
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            break

        if response.status_code >= 400:
            failures.append((row["Date"], response.status_code, response.text[:200]))
            print(f"FAIL {row['Date']}: HTTP {response.status_code} {response.text[:200]}")
        else:
            posted_seconds += row["Duration"]
            print(f"OK   {row['Date']}: {row['Duration'] / 3600:.2f}h")

        time.sleep(1.0)

    if dry_run:
        print(json.dumps(dry_run_list))

    # Reconcile against the source file so a partial import cannot pass unnoticed.
    print(f"\ndays processed : {len(modified_data)}")
    print(f"hours in CSV   : {csv_total_hours:.2f}")
    print(f"hours accepted : {posted_seconds / 3600:.2f}")
    if failures:
        print(f"FAILED         : {len(failures)} day(s)")
        for date, code, body in failures:
            print(f"  {date}  HTTP {code}  {body}")
        sys.exit(1)
    if abs(csv_total_hours - posted_seconds / 3600) > 0.01:
        print("MISMATCH: accepted hours do not equal the CSV total")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Parser for Harvest CSV ->\
                                     Toggle API")

    # Adding arguments
    parser.add_argument('-f', '--file', type=str, help='Filename',
                        required=True)
    parser.add_argument('-p', '--project', type=int, help='Project ID',
                        required=True)
    parser.add_argument('-n', '--name', type=str, help='Project Name',
                        required=True)
    parser.add_argument('-w', '--workspace', type=int, help='Workspace ID',
                        required=False)
    parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run',
                        required=False)

    args = parser.parse_args()

    # Set workspace_id if not provided
    workspace_id: int = args.workspace if args.workspace else WORKSPACE_ID

    # Parsing arguments
    if args and args.file and args.project and args.name and workspace_id:
        filename: str = args.file
        project_id: int = args.project
        project_name: str = args.name
        workspace_id: int = workspace_id
        dry_run: bool = args.dry_run
        read_file(filename, project_id, project_name, workspace_id, dry_run if dry_run else False)
    else:
        print("Invalid arguments")

if __name__ == "__main__":
    main()

