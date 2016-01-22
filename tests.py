# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from datetime import datetime
from unittest import TestCase

from pandas import Series, date_range

from get_fb_post_comments import (SeriesEncoder, intersect_timestamps,
    join_frequencies, calculate_frequencies)


class SeriesProcessionTestCase(TestCase):
    """
    Test calculation and merge of pandas.Series frames
    """

    def setUp(self):
        self.dr1 = date_range('2000-01-01 00:00:00', '2000-01-01 05:00:00',
                              freq='1H')
        self.dr2 = date_range('2000-01-01 04:00:00', '2000-01-01 10:00:00',
                              freq='1H')
        self.s1 = Series([1] * len(self.dr1), index=self.dr1)
        self.s2 = Series([1] * len(self.dr2), index=self.dr2)


    def test_series_json_encoder(self):
        reference = [
            [946684800, 1],
            [946688400, 1],
            [946692000, 1],
            [946695600, 1],
            [946699200, 1],
            [946702800, 1],
        ]

        res = json.dumps(self.s1, cls=SeriesEncoder)
        res1 = json.dumps(reference)

        self.assertEqual(res, res1, "SeriesEncoder doesn't work")


    def test_intersect_timestamps(self):
        ts1 = [
            datetime(2000, 1, 1, 0, 0, 0),
            datetime(2000, 1, 1, 1, 0, 0),
            datetime(2000, 1, 1, 2, 0, 0),
            datetime(2000, 1, 1, 3, 0, 0),
        ]

        ts_reverse_not_intersect = [
            datetime(2000, 1, 1, 7, 0, 0),
            datetime(2000, 1, 1, 6, 0, 0),
            datetime(2000, 1, 1, 5, 0, 0),
            datetime(2000, 1, 1, 4, 0, 0),
        ]

        chron_ts, reverse_ts, is_intersect = intersect_timestamps(
                                                ts1, ts_reverse_not_intersect)
        self.assertFalse(is_intersect,
                "Wrong intersection check for non overlaping sequencies")
        self.assertEqual(ts1, chron_ts, 'Chron sequence is wrong')
        self.assertEqual(ts_reverse_not_intersect, reverse_ts,
                         'Reverse chronological sequence is wrong')

        ts_reverse_intersect = [
            datetime(2000, 1, 1, 5, 0, 0),
            datetime(2000, 1, 1, 4, 0, 0),
            datetime(2000, 1, 1, 3, 0, 0),
            datetime(2000, 1, 1, 2, 0, 0),
        ]

        ts_reverse_intersect_result = [
            datetime(2000, 1, 1, 5, 0, 0),
            datetime(2000, 1, 1, 4, 0, 0),
        ]

        chron_ts, reverse_ts, is_intersect = intersect_timestamps(
                                                ts1, ts_reverse_intersect)
        self.assertTrue(is_intersect,
                "Wrong intersection check for overlaping sequencies")
        self.assertEqual(ts1, chron_ts, 'Chron sequence is wrong')
        self.assertEqual(ts_reverse_intersect_result, reverse_ts,
                         'Reverse chronological sequence is wrong')


    def test_join_frequencies(self):
        dr = date_range('2000-01-01 00:00:00', '2000-01-01 10:00:00', freq='1H')
        reference = Series([1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0,
                            1.0], index=dr)

        res = join_frequencies([self.s1, self.s2])

        self.assertTrue(res.equals(reference),
                        "join_frequencies() doesn't work")


    def test_calculate_frequencies(self):
        comment_datetimes = [
            datetime(2000, 1, 1, 0, 0, 0),
            datetime(2000, 1, 1, 0, 4, 0),
            datetime(2000, 1, 1, 0, 11, 0),
            datetime(2000, 1, 1, 0, 12, 0),
            datetime(2000, 1, 1, 0, 20, 0),
            datetime(2000, 1, 1, 0, 21, 0),
        ]

        dr = date_range('2000-01-01 00:05:00', '2000-01-01 00:25:00', freq='5Min')
        reference = Series([2.0, None, 2.0, None, 2.0], index=dr).dropna()

        res = calculate_frequencies(comment_datetimes)

        self.assertTrue(res.equals(reference),
                        "calculate_frequencies() doesn't work")
