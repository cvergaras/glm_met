import json
import os

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def nml_path():
    return os.path.join(FIXTURES, 'glm3.nml')


@pytest.fixture
def openmeteo_payload():
    with open(os.path.join(FIXTURES, 'openmeteo_sample.json')) as f:
        return json.load(f)


@pytest.fixture
def openmeteo_au_body():
    with open(os.path.join(FIXTURES, 'openmeteo_au_sample.json')) as f:
        return f.read()


@pytest.fixture
def silo_body():
    with open(os.path.join(FIXTURES, 'silo_sample.csv')) as f:
        return f.read()
