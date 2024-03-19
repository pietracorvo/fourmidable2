from control import controllers
from matplotlib import pyplot as plt
import numpy as np
import time
import threading

def show():
    x = 1
    for i in range(10):
        if x == 2:
            x = 1
        else:
            x = 2
        time.sleep(1)
        Rate = 5000
        output_signal_B = x * np.sin(np.linspace(0, 2 * np.pi, Rate + 1))
        output_signal_B = np.delete(output_signal_B, len(output_signal_B) - 1)
        out = np.zeros([3, Rate])
        out[1, :] = output_signal_B
        ni_control.change_output(out)

    Rate = 5000
    output_signal_B = 0 * np.sin(np.linspace(0, 2 * np.pi, Rate + 1))
    output_signal_B = np.delete(output_signal_B, len(output_signal_B) - 1)
    out = np.zeros([3, Rate])
    out[1, :] = output_signal_B
    ni_control.change_output(out)

magnets_fig = plt.figure()
# processed_fig = plt.figure()
# det_fig = plt.figure()


ni_control = controllers.NIcard(rate=5000)

Rate=27500
period = 0.5
output_signal_B = 0*np.sin(np.linspace(0, 2*np.pi, Rate+1))
output_signal_B = np.delete(output_signal_B, len(output_signal_B)-1)

out = np.zeros([3, Rate])
out[1, :] = output_signal_B

ni_control.start(output_signal=out)

# ni_control.start_plotting(processed_fig=processed_fig,
#                           fields_fig=magnets_fig,
#                           detectors_fig=det_fig)

ni_control.start_plotting(fields_fig=magnets_fig)

thr = threading.Thread(target=show)
thr.daemon = True
thr.start()

plt.show()

ni_control.stop()






