import pandas as pd
import matplotlib.pyplot as plt

with pd.HDFStore(r'C:\Users\user\Documents\Python\MOKEpy\gui\LoopTaking_20181025-141317.h5') as store:
    # get all the relevant data
    hp = dict()
    magnet = dict()
    for key in store.keys():
        split_key = key.split('/')
        if split_key[3] == "hexapole":
            magnet[split_key[2]] = store.get(key)
        elif split_key[3] == "hallprobe":
            hp[split_key[2]] = store.get(key)

hp_concat = pd.concat((h for h in hp.values()))
hp_means = hp_concat.groupby(hp_concat.index).mean()

magnet_concat = pd.concat((h for h in magnet.values()))
magnet_means = magnet_concat.groupby(magnet_concat.index).mean()

# reset indices. This is to aleviate ambiguity in concatinating
hp_means.reset_index(inplace=True, drop=True)
magnet_means.reset_index(inplace=True, drop=True)
all_concat = pd.merge_asof(hp_means, magnet_means, on="t")
all_concat.to_hdf('magnet_hysteresis.h5', key='data', data_columns=True, format="table")
for key in ["A", "B", "C"]:
    plt.plot(all_concat["magnet_"+key], all_concat["hallprobe_"+key], label = key)

plt.legend()
plt.xlabel('I [A]')
plt.ylabel('B [mT]')
plt.grid()
plt.show()
