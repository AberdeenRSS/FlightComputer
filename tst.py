from tests.hardware_tests.test_i2c import test_bno055
import asyncio
from logging import _nameToLevel, getLogger, StreamHandler
import sys

getLogger().setLevel(_nameToLevel['INFO'])

getLogger().addHandler(StreamHandler(sys.stdout))

asyncio.run(test_bno055())
