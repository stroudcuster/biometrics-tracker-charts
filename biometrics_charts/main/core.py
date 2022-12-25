from abc import abstractmethod
from collections import namedtuple
from datetime import datetime, time, timedelta
from decimal import Decimal
import threading
from typing import Callable, Optional

import numpy as np

import biometrics_tracker.ipc.messages as messages
import biometrics_tracker.ipc.queue_manager as queues
import biometrics_tracker.model.datapoints as dp
import biometrics_tracker.model.persistence as per
import biometrics_tracker.utilities.utilities as util

import biometrics_charts.model.data as chart_data
import biometrics_charts.model.time as chart_time


class PluginBase(threading.Thread):
    def __init__(self, queue_mgr: queues.Queues, person: dp.Person, start_dt: datetime, end_dt: datetime,
                 dp_type: dp.DataPointType):
        threading.Thread.__init__(self)
        self.queue_mgr = queue_mgr
        self.person: dp.Person = person
        self.start_dt: datetime = start_dt
        self.end_dt: datetime = end_dt
        self.dp_type: dp.DataPointType = dp_type

    def retrieve_datapoints(self, replyto: Callable) -> None:
        self.queue_mgr.send_db_req_msg(messages.DataPointReqMsg(destination=per.DataBase,
                                                                replyto=replyto,
                                                                operation=messages.DBOperation.RETRIEVE_SET,
                                                                person_id=self.person.id,
                                                                start=self.start_dt,
                                                                end=self.end_dt,
                                                                dp_type=self.dp_type))

    def run(self):
        self.retrieve_datapoints(replyto=self.produce_chart)
        msg: Optional[messages.DataPointRespMsg] = None
        while msg is None:
            msg = self.queue_mgr.check_db_resp_queue(block=False)
        msg.destination(msg)

    @abstractmethod
    def produce_chart(self, msg: messages.DataPointRespMsg):
        ...


time_range_type = namedtuple('TimeRange', ['min', 'max'])
value_range_type = namedtuple('ValueRange', ['min', 'max'])


def decimal_fill() -> Decimal:
    return Decimal(0)


def bp_fill() -> tuple[int, int]:
    return 0, 0


class ChartBase(PluginBase):
    def __init__(self, queue_mgr: queues.Queues, person: dp.Person, start_dt: datetime, end_dt: datetime,
                 dp_type: dp.DataPointType):
        PluginBase.__init__(self, queue_mgr, person, start_dt, end_dt, dp_type)
        self.min_max_times = chart_time.TimeMinMax(max=time(hour=0, minute=0, second=0),
                                                   min=time(hour=23, minute=59, second=59))
        self.type_min_max_times: dict[dp.DataPointType, chart_time.TimeMinMax] = {}
        self.min_max_values: dict[dp.DataPointType, chart_data.ValueMinMax] = {}
        self.raw_data: dict[dp.DataPointType, np.ndarray] = {}
        self.decimal_fill = np.vectorize(pyfunc=decimal_fill)
        self.bp_fill = np.vectorize(pyfunc=bp_fill)
        self.time_series: Optional[chart_time.TimeSeries] = None

    def find_min_max(self, datapoints: list[dp.DataPoint]):
        for datapoint in datapoints:
            if datapoint.taken.time() < self.min_max_times.min:
                self.min_max_times.min = datapoint.taken.time()
            if datapoint.taken.time() > self.min_max_times.max:
                self.min_max_times.max = datapoint.taken.time()
            if datapoint.type not in self.type_min_max_times:
                self.type_min_max_times[datapoint.type] = chart_time.TimeMinMax(max=time(hour=0, minute=0, second=0),
                                                                                min=time(hour=23, minute=59, second=59))
            if datapoint.taken.time() < self.type_min_max_times[datapoint.type].min:
                self.type_min_max_times[datapoint.type].min = datapoint.taken.time()
            if datapoint.taken.time() > self.type_min_max_times[datapoint.type].max:
                self.type_min_max_times[datapoint.type].max = datapoint.taken.time()

            if datapoint.type not in self.min_max_values:
                self.min_max_values[datapoint.type] = chart_data.ValueMinMax(min=99999, max=0, uom=datapoint.data.uom)
            match datapoint.type:
                case dp.DataPointType.BP:
                    data: dp.BloodPressure = datapoint.data
                    if self.min_max_values[datapoint.type].min > data.diastolic:
                        self.min_max_values[datapoint.type].min = data.diastolic
                    if self.min_max_values[datapoint.type].max < data.systolic:
                        self.min_max_values[datapoint.type].max = data.systolic
                case _:
                    if self.min_max_values[datapoint.type].min > datapoint.data.value:
                        self.min_max_values[datapoint.type].min = datapoint.data.value
                    if self.min_max_values[datapoint.type].max < datapoint.data.value:
                        self.min_max_values[datapoint.type].max = datapoint.data.value

    @abstractmethod
    def produce_chart(self, msg: messages.DataPointRespMsg) -> None:
        ...

    def create_time_series(self, interval: int = 120):
        min_time: datetime = util.mk_datetime(datetime.today(), self.min_max_times.min)
        max_time: datetime = util.mk_datetime(datetime.today(), self.min_max_times.max)
        tic_delta: timedelta = timedelta(seconds=interval*60)
        self.time_series = chart_time.TimeSeries(start=min_time, end=max_time, interval=tic_delta)

    def find_x_tic(self, dp_datetime: datetime) -> tuple[int, datetime]:
        return self.time_series.get_timepoint_by_time(dp_datetime)

    def prepare_data(self, datapoints: list[dp.DataPoint]):
        for row_idx, datapoint in enumerate(datapoints):
            if datapoint.type not in self.raw_data:
                shape = (len(datapoints), self.time_series.element_count())
                match datapoint.type:
                    case dp.DataPointType.BODY_WGT:
                        self.raw_data[datapoint.type] = np.ndarray(shape=shape, dtype=Decimal)
                        self.decimal_fill(self.raw_data[datapoint.type])
                    case dp.DataPointType.BODY_TEMP:
                        self.raw_data[datapoint.type] = np.ndarray(shape=shape, dtype=Decimal)
                        self.decimal_fill(self.raw_data[datapoint.type])
                    case dp.DataPointType.BP:
                        self.raw_data[datapoint.type] = np.ndarray(shape=shape, dtype=tuple[int, int])
                        self.bp_fill(self.raw_data[datapoint.type])
                    case dp.DataPointType.BG:
                        self.raw_data[datapoint.type] = np.ndarray(shape=shape, dtype=int)
                        self.raw_data[datapoint.type].fill(0)
                    case dp.DataPointType.PULSE:
                        self.raw_data[datapoint.type] = np.ndarray(shape=shape, dtype=int)
                        self.raw_data[datapoint.type].fill(0)
                    case _:
                        self.raw_data[datapoint.type] = np.ndarray(shape=(len(datapoints),
                                                                          self.time_series.element_count()), dtype=int)
                        self.raw_data[datapoint.type].fill(0)
            x_tic, x_datetime = self.find_x_tic(datapoint.taken)
            match datapoint.type:
                case dp.DataPointType.BP:
                    self.raw_data[datapoint.type][row_idx][x_tic] = (datapoint.data.systolic, datapoint.data.diastolic)
                case _:
                    self.raw_data[datapoint.type][row_idx][x_tic] = datapoint.data.value
        pass


class HourlyChart(ChartBase):
    def __init__(self, queue_mgr: queues.Queues, person: dp.Person, start_dt: datetime, end_dt: datetime,
                 dp_type: dp.DataPointType, interval: int):
        ChartBase.__init__(self, queue_mgr, person, start_dt, end_dt, dp_type)
        self.interval: int = interval

    def produce_chart(self, msg: messages.DataPointRespMsg):
        self.find_min_max(msg.datapoints)
        self.create_time_series(interval=self.interval)
        self.prepare_data(msg.datapoints)
        pass



