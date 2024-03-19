from control.instruments.moke import Moke
import h5py
import matplotlib.pyplot as plt

# the power supply needs to be plugged into the power supply port
duration = 2
if __name__ == "__main__":
    with Moke() as mk:
        ps = mk.instruments['groundedpin']
        start_time = ps.get_time()
        end_time = start_time + duration
        print('getting data...')
        with h5py.File('groundedpin_analysis.h5') as file:
            ps.save(file, start_time=start_time, end_time=end_time)
        data = ps.get_data(start_time=start_time, end_time=end_time)
        data.plot()
        plt.show()
