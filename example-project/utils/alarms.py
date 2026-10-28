#!/usr/bin/env python3

import eda_state as estate
from common.alarm_constants import SUBINTF_DOWN, BFD_SESSION_DOWN
from common.bfd import Peer
import re

SESSION_UP = "UP"


class CrNameAndSchema:
    def __init__(
            self,
            cr_name: str,
            schema: any):
        self.cr_name = cr_name
        self.schema = schema


def get_bfd_session_down_alarm_name(kind: str, resource_name: str, local_address: str) -> str:
    return f'{BFD_SESSION_DOWN}-{kind}-{resource_name}-localaddr-{local_address}'


def raise_bfd_session_down_alarm(schema, resource_name: str, node_name: str,
                                 local_address: str, down_reason: str, jspath: str,
                                 alarm_func):
    alarm_name = get_bfd_session_down_alarm_name(schema.kind, resource_name, local_address)
    alarm_func(
        name=get_k8s_compliant_alarm_name(alarm_name),
        resource=resource_name,
        kind=schema.kind,
        group=schema.group,
        probable_cause=f'BFD session is not up, {down_reason}',
        remedial_action='Verify the state of the BFD session.',
        jspath=jspath,
        targets_affected=[{"name": node_name}]
    )


def get_k8s_compliant_alarm_name(alarm_name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9.-]', '-', alarm_name)
