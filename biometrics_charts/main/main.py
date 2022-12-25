from datetime import datetime
import biometrics_tracker.model.datapoints as dp
import biometrics_tracker.ipc.queue_manager as queues

import biometrics_charts.main.core as core


def entry_point(queue_mgr: queues.Queues, person: dp.Person, start_dt: datetime, end_dt: datetime,
                dp_type: dp.DataPointType) -> None:
    ...


def hourly_chart_entry(queue_mgr: queues.Queues, person: dp.Person, start_dt: datetime, end_dt: datetime,
                       dp_type: dp.DataPointType) -> None:
    hourly_chart: core.HourlyChart = core.HourlyChart(queue_mgr=queue_mgr, person=person, start_dt=start_dt,
                                                      end_dt=end_dt, dp_type=dp_type, interval=120)
    hourly_chart.start()
    pass