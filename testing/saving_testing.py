from control.instruments.moke import Moke
from experiments.basic import sin_wave

if __name__=="__main__":
    with Moke() as mk:
        # start the experiment
        sin_wave(mk, period=0.5, amplitudes=(2, 0, 0))
