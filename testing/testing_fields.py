import numpy as np
import pandas as pd
if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.getcwd())
from control.instruments.moke import Moke
from gui.widgets.moke_docker import start_application


if __name__ == "__main__":
    t = np.linspace(0, 2 * np.pi, 100)
    data = np.zeros((len(t), 3))
    data[:, 0] += 10 * np.sin(t)
    with Moke() as mk:
        magnet = mk.instruments['hexapole']
        magnet.stage_interp(t, data)

        start_application(mk, ['hexapole', 'hallprobe'])
