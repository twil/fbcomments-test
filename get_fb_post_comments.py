#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import argparse
import readline

import requests


REPORT_TEMPLATE = 'templates/report.html'
REPORT_FILE_NAME = 'report.html'
DATA_FILE_NAME = 'data.json'

# Limit for the /comments edge
# We specially put a greater value - FB will limit it
COMMENTS_LIMIT = 10000
DEFAULT_AGGREGATION_INTERVAL = 5 # minutes

DEFAULT_CPUS_NUMBER = 4

# Graph API URLs
COMMENTS_EDGE = "https://graph.facebook.com/v2.5/{post_id}/comments?fields=created_time&limit={limit}&pretty=0&summary=1&filter=stream&access_token={access_token}"


def get_comments(post_id, access_token, limit=COMMENTS_LIMIT):
    """
    Run HTTP request and process it.
    
    Return: comments list, next page URL, cursor
    """

    url = COMMENTS_EDGE.format(post_id=post_id, limit=limit,
                               access_token=access_token)
    res = requests.get(url)
    json = res.json()

    data = json['data']
    if 'paging' in json:
        if 'next' in json['paging']:
            next_url = json['paging']['next']
        #if 'cursors' in json['paging'] and 'after' in json['paging']['cursors']:
            next_cursor = json['paging']['cursors']['after']

    return data, next_url, next_cursor

def calculate_frequencies(comments):
    return []

def save_report(frequencies, output_folder):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                description='Get a comments frequency for a FB post')
    parser.add_argument('post_id', type=str, help='FB post ID')
    parser.add_argument('access_token', type=str, help='Access Token')
    parser.add_argument('output_folder', type=str, help='Output folder')

    args = parser.parse_args()

    abs_path = os.path.abspath(args.output_folder)
    if os.path.exists(args.output_folder):
        answer = raw_input("""Are you sure you want to use this folder '%s'?
Existing '%s' and '%s' files will be overwritten.
Yes/no: """ % (abs_path, REPORT_FILE_NAME, DATA_FILE_NAME))
        if answer.lower() != 'yes':
            print('Exiting...')
            exit()
    else:
        os.mkdir(abs_path)

    comments, next_url, next_cursor = get_comments(args.post_id,
                                                   args.access_token)
    print(len(comments))
