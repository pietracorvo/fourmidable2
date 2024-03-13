import numpy as np

def save_calibration(instruments, group):
    for inst in instruments:
        inst_group = group.create_group(inst.name)
        inst_group.attrs['type'] = inst.calibration.__name__
        for key, value in inst.calib_params.items():
            if not isinstance(value, list):
                value = [value]
            inst_group.create_dataset(key, data=np.array(value))