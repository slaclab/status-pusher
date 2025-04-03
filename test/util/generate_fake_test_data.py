#!/usr/bin/python3
""" 
Generate fake test data on stdout for fettle-based status page report logs
"""
import csv
import datetime as dt
import io

DAYS = 90
START_DATE = dt.datetime.utcnow() - dt.timedelta(days=DAYS)
END_DATE = dt.datetime.utcnow()

FAKE_VALUE = 3.1415926535897


def gen_fake_log_data(
    start_date: dt.datetime = START_DATE,
    end_date: dt.datetime = END_DATE,
    fake_value: float = FAKE_VALUE,
) -> str:
    """
    Generate fake log data in csv format
    """
    dates = [
        start_date + dt.timedelta(days=d) for d in range((end_date - start_date).days)
    ]
    # note we want the spaces preceding the values to match Fettle's default format
    data = [
        [date.strftime("%Y-%m-%dT%H:%M:%SZ"), " success", f" {fake_value}"]
        for date in dates
    ]
    output = io.StringIO()
    writer = csv.writer(output, delimiter=",")
    writer.writerows(data)

    return output.getvalue()


if __name__ == "__main__":
    print(gen_fake_log_data())
