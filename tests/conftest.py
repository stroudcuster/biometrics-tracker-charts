from datetime import date
import pathlib
import pickle
import pytest
from typing import Optional

import biometrics_tracker.ipc.messages as msg
import biometrics_tracker.ipc.queue_manager as queue_manager
import biometrics_tracker.model.datapoints as dp


class QueueManagerPatch:
    """
    This class implements a monkey patch on the biometrics_tracker.ipc.Queues class and replaces the queue.Queue
    based dp_response and dp_request queues with lists.

    """
    def __init__(self):
        self.db_resp_queue: list[msg.MsgBase] = []
        self.completion_queue: list[msg.CompletionMsg] = []
        self.person: dp.Person = dp.Person(id='stroud', name='Stroud Custer', dob=date(year=1956, month=7, day=12))
        self.datapoints: Optional[list[dp.DataPoint]] = None
        cwd = pathlib.Path.cwd()
        while cwd.name != 'tests':
            cwd = cwd.parent
        with pathlib.Path(cwd, 'datapoints-2').open(mode='rb') as pf:
            unpickle = pickle.Unpickler(pf)
            self.datapoints: list[dp.DataPoint] = unpickle.load()

    def receive_db_resp(self, block: bool) -> msg.MsgBase:
        return self.db_resp_queue.pop()

    def send_db_req(self, message: msg.PersonReqMsg | msg.DataPointReqMsg) -> None:
        resp_msg = None
        match message.__class__:
            case msg.PersonReqMsg:
                resp_msg = msg.PersonMsg(destination=message.replyto, replyto=None, payload=self.person,
                                         operation=msg.DBOperation.RETRIEVE_SINGLE)
            case msg.DataPointReqMsg:
                payload: list[dp.DataPoint] = []
                for datapoint in self.datapoints:
                    if message.person_id is None or message.person_id == datapoint.person_id:
                        if message.start is None or message.start <= datapoint.taken:
                            if message.end is None or message.end >= datapoint.taken:
                                if message.dp_type is None or message.dp_type == datapoint.type:
                                    payload.append(datapoint)
                resp_msg = msg.DataPointRespMsg(destination=message.replyto, replyto=None, person_id=message.person_id,
                                                datapoints=payload)
        if resp_msg is not None:
            self.db_resp_queue.insert(0, resp_msg)


patch = QueueManagerPatch()


@pytest.fixture(autouse=True)
def check_db_resp_queue_filter(monkeypatch):
    monkeypatch.setattr(queue_manager.Queues, 'check_db_resp_queue', patch.receive_db_resp)


@pytest.fixture(autouse=True)
def send_db_req_msg_filter(monkeypatch):
    monkeypatch.setattr(queue_manager.Queues, 'send_db_req_msg', patch.send_db_req)

