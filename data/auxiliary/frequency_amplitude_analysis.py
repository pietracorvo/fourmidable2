import h5py
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
from tqdm import tqdm


def get_max_amp(fft_file, out_file):
    data = dict()
    out_data = {
        "hallprobe_amp": np.array([]),
        "hallprobe_freq": np.array([]),
        "hallprobe_phase": np.array([]),
        "hexapole_amp": np.array([]),
        "hexapole_freq": np.array([]),
        "hexapole_phase": np.array([])
    }
    with pd.HDFStore(fft_file) as store:
        for key in store.keys():
            split_key = key.split('/')
            device = split_key[2]
            data_name = split_key[1]
            if data_name not in data.keys():
                data[data_name] = dict()
            data[data_name][device] = store.get(key)

    for data_name, data_part in data.items():
        # to get the frequency with the highest amplitude and to make sure they are the same, first do the hexapole and
        # then the hallprobe based on the results from the hexapole
        for device_name in ['hexapole', 'hallprobe']:
            device_data = data_part[device_name]
            if device_name == 'hexapole':
                # find the index of maximal fft amplitude
                i = np.array(device_data["amplitude_A"]).argmax(axis=0)
                # get the frequency
                f = np.abs(device_data.loc[i, "frequency"])
            else:
                # the frequency has been defined, so just find the index of the closest frequency in hallprobe
                i = np.abs(np.array(device_data.loc[:, "frequency"] - f)).argmin(axis=0)
                # adjust the frequency (it should be the same or very close, but just as sanity check)
                f = np.abs(device_data.loc[i, "frequency"])
            out_data[device_name +
                     "_freq"] = np.append(out_data[device_name + "_freq"], f)
            out_data[device_name + "_amp"] = np.append(out_data[device_name + "_amp"], np.linalg.norm(
                device_data.loc[i, ["amplitude_A", "amplitude_B", "amplitude_C"]]))
            out_data[device_name + "_phase"] = np.append(out_data[device_name + "_phase"],
                                                         device_data.loc[i, "phase_A"])

    # turn the out_data to pandas df
    out_pd = pd.DataFrame.from_dict(out_data)

    with pd.HDFStore(out_file, 'w') as store:
        store.append('/data', out_pd, data_columns=True)


def plot_fft(data_file):
    with pd.HDFStore(data_file) as store:
        data = store.get("/data")

    plt.figure(figsize=(12, 4))
    plt.subplot(131)
    plt.scatter(data["hexapole_amp"], data["hallprobe_amp"],
                c=data["hallprobe_freq"])
    cbar = plt.colorbar()
    cbar.set_label('Hallprobe frequency')
    plt.xlabel('Input amplitude [mT]')
    plt.ylabel('Hallprobe amplitude [mT]')
    plt.grid()

    plt.subplot(132)
    # plt.scatter(data["hexapole_freq"], data["hallprobe_amp"]
    #             / data["hexapole_amp"], c=data["hexapole_amp"])
    plt.scatter(data["hexapole_freq"], data["hallprobe_amp"],
                c=data["hexapole_amp"])
    cbar = plt.colorbar()
    cbar.set_label('Input amplitude [mT]')
    plt.xlabel('Input frequency [Hz]')
    plt.ylabel('Hallprobe amplitude [mT]')
    plt.grid()

    plt.subplot(133)
    # get the phase difference. I add pi here because there is a known minus sign between inputs and hp signal
    phase_diff = data["hexapole_phase"] - data["hallprobe_phase"] + np.pi
    # translate so that it fits nicely
    phase_diff[phase_diff < 0] = phase_diff[phase_diff < 0] + np.pi
    # phase_diff -= 0.06 * data["hexapole_freq"]
    phase_diff[phase_diff > 2 *
               np.pi] = phase_diff[phase_diff > 2 * np.pi] - 2 * np.pi
    # plt.scatter(data["hexapole_freq"], np.sin(
    #     phase_diff), c=data["hexapole_amp"])
    plt.scatter(data["hexapole_freq"], phase_diff, c=data["hexapole_amp"])
    cbar = plt.colorbar()
    cbar.set_label('Input amplitude [mT]')
    plt.xlabel('Input frequency [Hz]')
    # plt.ylabel('Hallprobe sin(phase difference)')
    plt.ylabel('Hallprobe phase difference')
    plt.grid()

    plt.tight_layout(pad=0.3, w_pad=1, h_pad=1)

    plt.show()


def collect_fft(folder_in, file_out):
    """Extracts the data and collects fft of all the loops.
    If invert_hp is True and invert_fun is given, the nonlinear response of the magnet is removed via the invert_fun
    """
    wlk = list(os.walk(folder_in))
    folder = wlk[0][0]
    # select the files with correct extension
    files = [f for f in wlk[0][2] if f.split('.')[1] == "h5"]

    out_store = pd.HDFStore(file_out, 'w')

    # prepare the data dictionary
    data = {
        "hexapole": dict(),
        "hallprobe": dict()
    }
    fft_data = {
        "hallprobe": None,
        "hexapole": None
    }

    # iterate over the files and get freq/amp
    for i, f in enumerate(tqdm(files)):
        with h5py.File(os.path.join(folder, f), 'r') as file:
            # get all the relevant data
            grp = file['loops']
            for loop in grp.keys():
                device_grp = grp[loop]
                for device in device_grp.keys():
                    if device in {"hexapole", "hallprobe"}:
                        device_data = device_grp.get(device + '/data')[:]
                        data[device][loop] = device_data[:, 1:]
                        # get the timestep (assume all equal, I know I am doing this every time, but it's easier)
                        timestep = device_data[1, 0] - device_data[0, 0]

        for dev in data:
            concat = np.vstack((h for h in data[dev].values()))
            # get the fourier transform
            n = concat.shape[0]
            fft = np.fft.rfft(concat, axis=0) / (n / 2)
            fft_phase = np.angle(fft)
            fft_amp = np.absolute(fft)
            freq = np.fft.rfftfreq(n, d=timestep)

            fft_data[dev] = pd.DataFrame(np.hstack((freq[:, None], fft_amp, fft_phase)),
                                         columns=["frequency", "amplitude_A", "amplitude_B", "amplitude_C",
                                                  "phase_A", "phase_B", "phase_C"])
            # having the fft, save the data
            out_store.put("/data_" + str(i) + "/" + dev,
                          fft_data[dev], format="table", data_columns=True)
    out_store.close()


def plot_amp(data_file):
    with pd.HDFStore(data_file) as store:
        data = store.get("/data")

    plt.scatter(data["hexapole_freq"], data["hallprobe_amp"])
    plt.xlabel('Magnet frequency [Hz]')
    plt.ylabel('Hallprobe amplitude [mT]')
    plt.grid()
    plt.title('2A magnet amplitude')

    # plt.tight_layout(pad=0.3, w_pad=1, h_pad=1)
    plt.show()

# def invert_fun(x, A=9.6, b=1.01, c=3.49):
#     """Function designed to invert the effect of magnet nonlinearity"""
#     u = b*x/2
#     idx = np.abs(u)>1
#     if np.any(idx):
#         print('Value outside predicted range!')
#         print(x[np.argmax(np.abs(u))])
#     u[idx] = 0.9*np.sign(u[idx])
#     return A*np.arctanh(-u)+c*x

if __name__ == "__main__":
    folder = r"C:\Users\user\Documents\3DMOKE\Calibration data\FreqAmp_Vchannel"
    # folder = "/home/luka/OneDrive/PhD/3DMOKE/Calibration data/Freq_amp_extinction"
    file_fft = "freq_amplitude_fft.h5"
    file_max_amp = "freq_amplitude_max.h5"
    collect_fft(folder, file_fft)
    get_max_amp(file_fft, file_max_amp)
    plot_fft(file_max_amp)
    # plot_amp(file_max_amp)
