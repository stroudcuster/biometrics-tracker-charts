from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional

import biometrics_tracker.model.datapoints as dp
import biometrics_tracker.model.uoms as uoms
import biometrics_charts.model.time as time


class Datum:
    def __init__(self, datapoint: dp.DataPoint):
        self.datapoint = datapoint
        self.ts_idx: Optional[int] = None
        self.normal_value: Optional[int | Decimal | tuple[int, int]] = None

    def set_timeseries_idx(self, timeseries: time.TimeSeries):
        self.ts_idx = timeseries.get_timepoint_by_time(self.datapoint.taken)

    def set_normal_value(self, range: Decimal, func: Callable):
        self.normal_value = func(datapoint=self.datapoint)


@dataclass
class ValueMinMax:
    min: int | Decimal
    max: int | Decimal
    uom: uoms.UOM
