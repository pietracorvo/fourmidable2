import pandas as pd
import numpy as np
from experiments.skm import process_skm
import matplotlib.pyplot as plt

nc = pd.read_pickle('../experiments/nc')
woll = pd.read_pickle('../experiments/woll')

image = process_skm(nc, woll, 29)

plt.imshow(image)
plt.show(block=True)
