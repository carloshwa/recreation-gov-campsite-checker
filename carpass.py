#!/usr/bin/env python3

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta

import requests
from fake_useragent import UserAgent

LOG = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(process)s - %(levelname)s - %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
LOG.addHandler(sh)


BASE_URL = "https://www.recreation.gov"
AVAILABILITY_ENDPOINT = "/api/ticket/availability/facility/"

INPUT_DATE_FORMAT = "%Y-%m-%d"

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"

headers = {"User-Agent": UserAgent().random}


def format_date(date_object):
    date_formatted = datetime.strftime(date_object, "%Y-%m-%d")
    return date_formatted


def generate_params(start):
    params = {"date": format_date(start)}
    return params


def send_request(url, params):
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            "failedRequest",
            "ERROR, {} code received from {}: {}".format(
                resp.status_code, url, resp.text
            ),
        )
    return resp.json()


def get_park_information(park_id, params):
    url = "{}{}{}".format(BASE_URL, AVAILABILITY_ENDPOINT, park_id)
    LOG.debug("Querying for {} with these params: {}".format(url, params))
    return send_request(url, params)


def get_num_available_sites(resp):
    primary = resp[0]["booking_windows"]["PRIMARY"]["advanced_sales_details"]["threshold_exists"]
    secondary = resp[0]["booking_windows"]["SECONDARY"]["advanced_sales_details"]["threshold_exists"]
    LOG.debug("primary: {}, secondary: {}".format(primary, secondary))

    num_available = 0
    if primary:
        num_available += 1
    if secondary:
        num_available += 1

    return num_available


def valid_date(s):
    try:
        return datetime.strptime(s, INPUT_DATE_FORMAT)
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def _main(parks):
    out = []
    availabilities = False
    for park_id in parks:
        params = generate_params(args.start_date)
        LOG.debug("Querying for {} with these params: {}".format(park_id, params))
        park_information = get_park_information(park_id, params)
        LOG.debug(
            "Information for {}: {}".format(
                park_id, json.dumps(park_information, indent=1)
            )
        )
        current = get_num_available_sites(
            park_information
        )
        if current:
            emoji = SUCCESS_EMOJI
            availabilities = True
        else:
            emoji = FAILURE_EMOJI

        out.append(
            "{} {}: {} pass(es) available".format(
                emoji, park_id, current
            )
        )

    if availabilities:
        print(
            "There are passes available for {}!!!".format(
                args.start_date.strftime(INPUT_DATE_FORMAT)
            )
        )
    else:
        print("There are no passes available :(")
    print("\n".join(out))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", "-d", action="store_true", help="Debug log level")
    parser.add_argument(
        "--start-date", required=True, help="Start date [YYYY-MM-DD]", type=valid_date
    )

    parser.add_argument(
        dest="parks", metavar="park", nargs="+", help="Park ID(s)", type=int
    )
    parser.add_argument(
        "--stdin",
        "-",
        action="store_true",
        help="Read list of park ID(s) from stdin instead",
    )

    args = parser.parse_args()

    if args.debug:
        LOG.setLevel(logging.DEBUG)

    parks = args.parks or [p.strip() for p in sys.stdin]

    try:
        _main(parks)
    except Exception:
        print("Something went wrong")
        raise
