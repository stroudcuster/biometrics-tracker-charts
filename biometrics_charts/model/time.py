import collections
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from functools import lru_cache
from typing import Optional

import biometrics_tracker.utilities.utilities as util

class TimeSeries:
    def __init__(self, start: datetime, end: datetime, interval: timedelta):
        self.start: datetime = start
        self.end: datetime = end
        self.full_span: timedelta = self.end - self.start
        self.interval: timedelta = interval
        self.map: collections.OrderedDict[int, datetime] = collections.OrderedDict()
        dt: datetime = self.start
        idx: int = 0
        while dt < self.end:
            self.map[idx] = dt
            dt = dt + interval
            idx += 1
        if self.map[idx - 1] != self.end:
            self.map[idx] = self.end

    def element_count(self) -> int:
        return len(self.map)

    def get_timepoint_by_idx(self, idx: int) -> datetime:
        return self.map[idx]

    @lru_cache
    def get_timepoint_by_time(self, srch_time: datetime) -> tuple[Optional[int], Optional[datetime]]:
        norm_time = util.mk_datetime(self.start.date(), srch_time.time())
        if self.start <= norm_time <= self.end:
            span: timedelta = norm_time - self.start
            # idx = int((span.seconds / self.full_span.seconds) * self.element_count()) - 1
            idx = 0
            while idx < self.element_count()-1:
                tp: datetime = self.get_timepoint_by_idx(idx)
                if tp <= norm_time < self.get_timepoint_by_idx(idx+1):
                    return idx, tp
                idx += 1
            return idx, self.get_timepoint_by_idx(idx)
        else:
            return None, None

@dataclass
class TimeMinMax:
    min: time
    max: time


if __name__ == '__main__':
    now = datetime.now()
    later = now + timedelta(hours=8)
    ts = TimeSeries(start=now, end=later, interval=timedelta(minutes=15))
    tp1: datetime = ts.get_timepoint_by_idx(ts.element_count()//3)
    idx, tp2 = ts.get_timepoint_by_time(srch_time=datetime(year=now.year, month=now.month, day=now.day,
                                                           hour=20, minute=30, second=15))
    pass




