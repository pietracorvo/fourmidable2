from instrumental.drivers.daq.ni import NIDAQ, Task
from instrumental import u
import numpy as np

daq = NIDAQ('Dev1')
prt = daq.port0
prt = prt[0].as_input()

task = Task(prt, daq.ai0)

task.set_timing(duration='1s', fsamp='10000Hz')
result = task.run()

task.unreserve()
task.clear()
# print(result)