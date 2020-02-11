#!/usr/bin/env python3

import argparse
import json
import logging
from datetime import datetime, timedelta

import requests
from fake_useragent import UserAgent
from flask import Flask, request
from mailjet_rest import Client
import os

mailjet_api_key = os.environ['MAILJET_API_KEY']
mailjet_api_secret = os.environ['MAILJET_API_SECRET']
mailjet_from = os.environ['MAILJET_FROM']
mailjet_to = os.environ['MAILJET_TO']
mailjet = Client(auth=(mailjet_api_key, mailjet_api_secret), version='v3.1')

mailjet_data = {
    'Messages': [
        {
            "From": {
                "Email": mailjet_from
            },
            "To": [
                {
                    "Email": mailjet_to,
                }
            ],
            "Subject": "Campsite checker",
        }
    ]
}

app = Flask(__name__)

LOG = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(process)s - %(levelname)s - %(message)s")
sh = logging.StreamHandler()
sh.setFormatter(formatter)
LOG.addHandler(sh)

BASE_URL = "https://www.recreation.gov"
AVAILABILITY_ENDPOINT = "/api/camps/availability/campground/"
MAIN_PAGE_ENDPOINT = "/api/camps/campgrounds/"

INPUT_DATE_FORMAT = "%Y-%m-%d"

SUCCESS_EMOJI = "🏕"
FAILURE_EMOJI = "❌"

headers = {"User-Agent": UserAgent().random}


def format_date(date_object):
    date_formatted = datetime.strftime(date_object, "%Y-%m-%dT00:00:00Z")
    return date_formatted


def generate_params(start, end):
    params = {"start_date": format_date(start), "end_date": format_date(end)}
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
    return send_request(url, params)


def get_name_of_site(park_id):
    url = "{}{}{}".format(BASE_URL, MAIN_PAGE_ENDPOINT, park_id)
    resp = send_request(url, {})
    return resp["campground"]["facility_name"]


def get_num_available_sites(resp, start_date, end_date):
    maximum = resp["count"]

    num_available = 0
    num_days = (end_date - start_date).days
    dates = [end_date - timedelta(days=i) for i in range(1, num_days + 1)]
    dates = set(format_date(i) for i in dates)
    for site in resp["campsites"].values():
        available = bool(len(site["availabilities"]))
        for date, status in site["availabilities"].items():
            if date not in dates:
                continue
            if status != "Available":
                available = False
                break
        if available:
            num_available += 1
            LOG.debug("Available site {}: {}".format(num_available, json.dumps(site, indent=1)))
    return num_available, maximum


def valid_date(s):
    try:
        return datetime.strptime(s, INPUT_DATE_FORMAT)
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


@app.route('/check/<park_id>')
def check(park_id):
    key = request.args.get('key')
    if key != os.environ["KEY"]:
        return "No data."

    start_date = datetime.strptime(request.args.get('start_date'), "%Y-%m-%d")
    end_date = datetime.strptime(request.args.get('end_date'), "%Y-%m-%d")

    availabilities = False
    params = generate_params(start_date, end_date)
    LOG.debug("Querying for {} with these params: {}".format(park_id, params))
    park_information = get_park_information(park_id, params)
    LOG.debug(
        "Information for {}: {}".format(
            park_id, json.dumps(park_information, indent=1)
        )
    )
    name_of_site = get_name_of_site(park_id)
    current, maximum = get_num_available_sites(
        park_information, start_date, end_date
    )
    if current:
        emoji = SUCCESS_EMOJI
        availabilities = True
    else:
        emoji = FAILURE_EMOJI

    result = "{} {} ({}): {} site(s) available out of {} site(s)\n".format(
            emoji, name_of_site, park_id, current, maximum
        )

    if availabilities:
        result += "There are campsites available from {} to {}!!!".format(
                start_date.strftime(INPUT_DATE_FORMAT),
                end_date.strftime(INPUT_DATE_FORMAT),
            )

        mailjet_data['Messages'][0]["TextPart"] = result
        mailjet_result = mailjet.send.create(data=mailjet_data)
        print(mailjet_result.status_code)
        print(mailjet_result.json())
    else:
        result += "There are no campsites available :("

    return result


if __name__ == "__main__":
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
