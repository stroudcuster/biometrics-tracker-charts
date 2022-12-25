from datetime import date, datetime
import pytest

import biometrics_charts.main.core as core

import biometrics_tracker.model.datapoints as dp
import biometrics_tracker.ipc.queue_manager as queues


def test_hourly_chart():
    queue_mgr: queues.Queues = queues.Queues(sleep_seconds=2)
    person: dp.Person = dp.Person(id='stroud', name='Stroud Custer', dob=date(year=1956, month=11, day=5))
    hourly_chart: core.HourlyChart = core.HourlyChart(queue_mgr=queue_mgr,
                                                      person=person,
                                                      start_dt=datetime(year=2022, month=9, day=1,
                                                                        hour=0, minute=0, second=0),
                                                      end_dt=datetime(year=2022, month=12, day=31,
                                                                      hour=23, minute=59, second=59),
                                                      dp_type=dp.DataPointType.BG, interval=120)
    hourly_chart.start()
    hourly_chart.join()
    pass


