#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import signal
import argparse
import readline
from datetime import datetime
from multiprocessing import Pool, cpu_count
import json
import time
from itertools import imap

import requests
import numpy
from pandas import Series, date_range

DEBUG_TIMING = False

REPORT_TEMPLATE = 'templates/report.html'
REPORT_FILE_NAME = 'report.html'
DATA_FILE_NAME = 'data.js'

# Limit for the /comments edge
# We specially put a greater value - FB will limit it
COMMENTS_LIMIT = 10000
DEFAULT_AGGREGATION_INTERVAL = '5Min'
DEFAULT_PROCESS_TIMEOUT = 60

ORDER_CHRONOLOGICAL = 'chronological'
ORDER_REVERSE_CHRONOLOGICAL = 'reverse_chronological'
DEFAULT_ORDER = ORDER_CHRONOLOGICAL

DEFAULT_CPUS_NUMBER = 4

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Graph API URLs
COMMENTS_EDGE = "https://graph.facebook.com/v2.5/{post_id}/comments?fields=created_time&limit={limit}&pretty=0&summary=1&filter=stream&order={order}&access_token={access_token}"


class SeriesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Series):
            return [(_to_timestamp(i), v) for i, v in obj.iteritems()]
        else:
            return super(SeriesEncoder, self).default(obj)


def start_processing_comments(post_id, access_token, limit=COMMENTS_LIMIT):
    """
    Init URL for a first request

    TODO: we need to control this function. pass pool as an argument?
    """

    url_chron = COMMENTS_EDGE.format(post_id=post_id, limit=limit,
                                     order=ORDER_CHRONOLOGICAL,
                                     access_token=access_token)
    url_reverse = COMMENTS_EDGE.format(post_id=post_id, limit=limit,
                                     order=ORDER_REVERSE_CHRONOLOGICAL,
                                     access_token=access_token)

    cpus = DEFAULT_CPUS_NUMBER
    try:
        cpus = cpu_count()
    except NotImplementedError:
        pass
    pool = Pool(processes=cpus, initializer=_init_worker)

    if DEBUG_TIMING:
        t_start = time.time()

    timestamps_chron = []
    timestamps_reverse = []
    while True:
        try:
            #(res_chron, res_reverse) = map(request_comments, [url_chron,
            #                                                  url_reverse])

            # 2x performance boost
            (res_chron, res_reverse) = pool.map(request_comments, [url_chron,
                                                                   url_reverse])

            url_chron = res_chron[1]
            url_reverse = res_reverse[1]
    
            chron_timestamps, reverse_timestamps, is_intersect = \
                if_timestamps_intersect(res_chron[0], res_reverse[0])
    
            timestamps_chron.append(chron_timestamps)
            # in place
            reverse_timestamps.reverse()
            timestamps_reverse.append(reverse_timestamps)
    
            if is_intersect:
                break
        except (KeyboardInterrupt, SystemExit):
            pool.terminate()
            print('Exiting...')
            exit()

    if DEBUG_TIMING:
        print("Recieved comments in %s seconds" % (time.time() - t_start))
        t_start = time.time()

    # Process timestamps
    # in place
    # 7 orders faster then HTTP requests
    timestamps_reverse.reverse()
    timestamps_chron.extend(timestamps_reverse)

    if DEBUG_TIMING:
        print("Combined timestamps in %s seconds" % (time.time() - t_start))
        t_start = time.time()

    #fs = pool.map(calculate_frequencies, timestamps_chron)

    # 2x boost. looks like data transfer between processes takes a lot of time
    # and calculations are pretty simple.
    # 3 orders faster then HTTP requests
    fs = imap(calculate_frequencies, timestamps_chron)
    frequencies = join_frequencies(fs)

    if DEBUG_TIMING:
        print("Calculated frequencies in %s seconds" % (time.time() - t_start))

    return frequencies


def if_timestamps_intersect(chron_timestamps, reverse_timestamps):
    """
    Check if chron_timestamps[-1] timestamp is > then reverse_timestamps[-1]
    and return shrinked reverse_timestamps
    """

    is_intersect = False

    ts_right = chron_timestamps[-1]
    ts_left = reverse_timestamps[-1]

    # we hit the middle. drop extra values
    if ts_right >= ts_left:
        is_intersect = True
        try:
            i = reverse_timestamps.index(ts_right)
            reverse_timestamps = reverse_timestamps[:i]
        # if index is not found then ts_left < res_chron[0][0]
        except ValueError:
            reverse_timestamps = []

    return chron_timestamps, reverse_timestamps, is_intersect


def join_frequencies(fs):
    """
    fs is a list of lists, eg.
    [
        [<timestamp>, <comments_count>],
        [<timestamp>, <comments_count>],
        ...
    ]
    """

    frequencies = None
    for f in fs:
        if frequencies is None:
            frequencies = f
            continue
        frequencies = frequencies.add(f, fill_value=0)

    return frequencies


def request_comments(url):
    """
    Run HTTP request and process it.
    
    Return: comments list, next page URL, cursor
    """

    res = requests.get(url)
    json = res.json()

    # created_time is in UTC
    timestamps = [datetime.strptime(c['created_time'], '%Y-%m-%dT%H:%M:%S+0000') for c in json['data']]
    next_url = None
    cursor = None
    if 'paging' in json:
        if 'next' in json['paging']:
            next_url = json['paging']['next']
        if 'cursors' in json['paging'] and 'after' in json['paging']['cursors']:
            cursor = json['paging']['cursors']['after']

    return timestamps, next_url, cursor


def calculate_frequencies(comments,
                          aggregation_interval=DEFAULT_AGGREGATION_INTERVAL):
    s = Series([1] * len(comments), comments)
    freq = s.resample(aggregation_interval, how='sum', label='right')

    #return freq.fillna(0)
    freq.dropna(inplace=True)
    return freq


def save_report(output_folder, frequencies,
                interval=DEFAULT_AGGREGATION_INTERVAL, **kwargs):
    """
    Save frequencies and meta data + html template in a specified folder

    `kwargs` contains post_id and might have additional meta data
    """

    data = {
        "interval": interval,
        "data": frequencies,
    }
    data.update(kwargs)

    # report.html template
    with open(os.path.join(BASE_DIR, REPORT_TEMPLATE)) as f:
        template = f.read()

    template = template.replace('{{ post_id }}', kwargs.get('post_id', ''))
    template = template.replace('{{ interval }}', interval)

    with open(os.path.join(output_folder, REPORT_FILE_NAME), 'w') as f:
        f.write(template)

    with open(os.path.join(output_folder, DATA_FILE_NAME), 'w') as f:
        f.write('var frequencies = ')
        json.dump(data, f, indent=2, cls=SeriesEncoder)
        f.write(';')


def _init_worker():
    """
    Hide SIGINT from a worker
    """

    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _to_timestamp(d):
    """
    Convert datetime to UTC timestamp

    d must be in UTC
    """

    return int((d - datetime(1970, 1, 1)).total_seconds())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                description='Get a comments frequency for a FB post')
    parser.add_argument('--time', action='store_true',
                        help='Time critical places')
    parser.add_argument('--yes', action='store_true',
                        help='Force "yes" answers')
    parser.add_argument('post_id', type=str, help='FB post ID')
    parser.add_argument('access_token', type=str, help='Access Token')
    parser.add_argument('output_folder', type=str, help='Output folder')

    args = parser.parse_args()

    abs_path = os.path.abspath(args.output_folder)
    if os.path.exists(args.output_folder) and not args.yes:
        answer = raw_input("""Are you sure you want to use this folder '%s'?
Existing '%s' and '%s' files will be overwritten.
Yes/no: """ % (abs_path, REPORT_FILE_NAME, DATA_FILE_NAME))
        if answer.lower() != 'yes':
            print('Exiting...')
            exit()
    elif args.yes:
        print("Overwritting '%s' and '%s' files." % (REPORT_FILE_NAME,
                                                     DATA_FILE_NAME))
    else:
        os.mkdir(abs_path)

    # debug timing
    # HACK: global state
    if args.time:
        DEBUG_TIMING = True

    frequencies = start_processing_comments(args.post_id, args.access_token)
    save_report(abs_path, frequencies, post_id=args.post_id)
