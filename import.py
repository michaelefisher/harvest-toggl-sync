#!/usr/bin/env python3

import argparse
import csv
import itertools
import os
from base64 import b64encode
from datetime import datetime
from typing import Dict, List

import requests

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


def read_file(file: str, project_id: int, project_name: str, workspace_id: int
              = WORKSPACE_ID, dry_run: bool = False):

    modified_data: List[Dict[bytes, bytes]] = []

    with open(file, "r") as file:
        reader = csv.DictReader(file)
        next(reader)

        # Sort and group the rows by the first column - Date
        sorted_rows = sorted(reader, key=lambda row: row["Date"])

        for date, rows in group_by_date(sorted_rows):
            for updated_data in add_hours_for_day(rows):
                modified_data.append(updated_data)

    print("Modified data: ", modified_data)

    for row in modified_data:
        if not dry_run:
            data = requests.post(
                f"https://api.track.toggl.com/api/v9/workspaces/{WORKSPACE_ID}/time_entries?meta=true",
                json={
                    "billable": True,
                    "created_with": "python-toggl",
                    "description": "Software development",
                    "duration": int(row["Total Hours"]),
                    "project_id": project_id,
                    "start": format_datetime(row["Date"]),
                    "wid": workspace_id,
                    "workspace_id": workspace_id,
                },
                headers={
                    "content-type": "application/json",
                    "Authorization": "Basic %s" % b64encode(toggl_api_key).decode("ascii"),
                },
            )
            print(data.json())
        else:
            print(json.pprint({
                "billable": True,
                "created_with": "python-toggl",
                "description": "Software development",
                "duration": int(row["Total Hours"]),
                "project_id": project_id,
                "start": format_datetime(row["Date"]),
                "wid": workspace_id,
                "workspace_id": workspace_id,
            }))

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

    # Parsing arguments
    args = parser.parse_args()
    if args and args.file and args.project and args.name and args.workspace and args.dry_run:
        filename = args.file
        project_id = args.project
        project_name = args.name
        workspace_id = args.workspace
        dry_run = args.dry_run
        read_file(filename, project_id, project_name, workspace_id)
    elif args and args.file and args.project and args.name and args.dry_run:
        filename = args.file
        project_id = args.project
        project_name = args.name
        read_file(filename, project_id, project_name)
        dry_run = args.dry_run
    else:
        print("Invalid arguments")

if __name__ == "__main__":
    main()

