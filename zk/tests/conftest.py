# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time

import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import RetryError, docker_run
from datadog_checks.zk import ZookeeperCheck
from datadog_checks.zk.zk import ZKConnectionFailure

CHECK_NAME = 'zk'
HOST = get_docker_hostname()
PORT = 12181
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)


VALID_CONFIG = {'host': HOST, 'port': PORT, 'expected_mode': "standalone", 'tags': ["mytag"]}

STATUS_TYPES = ['leader', 'follower', 'observer', 'standalone', 'down', 'inactive', 'unknown']


@pytest.fixture(scope="session")
def get_instance():
    return VALID_CONFIG


@pytest.fixture
def get_invalid_mode_instance():
    return {'host': HOST, 'port': PORT, 'expected_mode': "follower", 'tags': []}


@pytest.fixture
def get_conn_failure_config():
    return {'host': HOST, 'port': 2182, 'expected_mode': "down", 'tags': []}


def get_version():
    zk_version = os.environ.get("ZK_VERSION")
    version = [int(k) for k in zk_version.split(".")]
    if len(version) == 2:
        version += [0]
    return version


@pytest.fixture(scope="session")
def dd_environment(get_instance):
    def condition():
        sys.stderr.write("Waiting for ZK to boot...\n")
        booted = False
        dummy_instance = {'host': HOST, 'port': PORT, 'timeout': 500}
        for _ in range(10):
            try:
                out = ZookeeperCheck('zk', {}, [dummy_instance])._send_command('ruok')
                out.seek(0)
                if out.readline() != 'imok':
                    raise ZKConnectionFailure()
                booted = True
                break
            except ZKConnectionFailure:
                time.sleep(1)

        if not booted:
            raise RetryError("Zookeeper failed to boot!")
        sys.stderr.write("ZK boot complete.\n")

    compose_file = os.path.join(HERE, 'compose', 'zk.yaml')
    if [3, 5, 0] <= get_version() < [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk35.yaml')
    elif get_version() >= [3, 6, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk36plus.yaml')

    with docker_run(compose_file, conditions=[condition]):
        yield get_instance
