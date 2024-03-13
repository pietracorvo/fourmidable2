from experiments.basic import *
from termcolor import colored
from data.saving import  MokeSaver


def field_mapping(moke):
    """Starts a chirp signal wave output to each of the dipoles

    Args:
        moke: handle to moke object
    """

    # get ni and stage handles for convenience
    magnet = moke.instruments['hexapole']
    hallprobe = moke.instruments['hallprobe']
    bighallprobe = moke.instruments['bighall_fields']
    linearstage = moke.instruments['stage'].instruments['linear_stage']
    allowed_temperature = 55
    max_move_time = 120
    movement_blocked = False
    i_start = 38

    # define the experiment timing
    degauss_time = 3
    field_acquisition_time = 0.25
    field_buffer_time = 0.5
    # strength of the fields
    field_strength = 1.5

    # get position parameters
    side_length = 2 * 10 ** 3
    resolution = 0.1125 * 10 ** 3
    # get the cube points
    positions = signals.get_cube_points(side_length, resolution)
    # get only the zero z
    ## 2D map
    # positions = positions[positions[:, 2] == 0, :]
    ## set the current position to be the center
    # positions[:, [0, 1]] = positions[:, [0, 1]] - side_length / 2
    ## for xz scan, switch y and z
    # positions = positions[:, [0, 2, 1]]

    # 3D map
    positions = positions - side_length / 2
    # print(positions)
    # print number of positions and required time
    print('Number of positions: ', len(positions))

    # prepare the signals
    zeros_time = 5
    degauss_fun, dz_time = signals.stack_funs([signals.get_deGaussing_fun(), lambda x: np.zeros(len(x))],
                                              [degauss_time, zeros_time])
    degauss_signal = [degauss_fun] * 3
    const_field_signals = [
        signals.get_const_signal([field_strength, 0, 0]),
        signals.get_const_signal([field_strength, field_strength, 0]),
        signals.get_const_signal([field_strength, field_strength, field_strength]),
    ]

    # give the approximate value of the required time
    stage_move_time = linearstage.instruments['newport'].time_to_position(
        list(np.array(positions[0, :]) - np.array(positions[1, :])), relative=True)
    print('Approximate required time: ',
          (np.max([degauss_time, stage_move_time]) + 3 * (field_buffer_time + field_acquisition_time)) * len(
              positions) / 3600, ' hrs')

    # create a file to save the experiment in
    filename = "field_map" + time.strftime("%Y%m%d-%H%M") + '.h5'
    with h5py.File(filename, 'w') as file:
        # set zero time and start applying the signal
        for i, pos in enumerate(positions):
            if i + 1 < i_start:
                continue
            # degauss
            magnet.stage_data(degauss_signal, dz_time, autostart=True)
            t0 = magnet.get_time()
            # set the given position
            linearstage.set_position(pos, wait=False)
            print('Position ', i + 1, '/', len(positions))
            # create position group
            pos_grp = file.create_group('position' + str(i))
            hallprobe.wait_for_time(t0 + degauss_time + 1)
            magnet.stage_data(signals.get_const_signal([0, 0, 0]), 1, autostart=True)

            move_time = 0
            while True:
                time.sleep(0.05)
                if not linearstage.is_moving():
                    break
                move_time += 0.05
                if move_time > max_move_time and i>0:
                    movement_blocked = True
                    print(colored('Stage not moving! Stopping...', 'red'))
                    break
            if movement_blocked:
                break
            # save the stage position
            linearstage.save(pos_grp)

            # check the temperature and let it cool down if it is too high
            if temp_too_high(moke, allowed_temperature):
                while temp_too_high(moke, allowed_temperature - 10):
                    print('Temperature too high, will wait until it goes below ', allowed_temperature - 10)
                    time.sleep(5)
                    continue

            # apply the fields and save the values
            for j, s in enumerate(const_field_signals):
                # apply the field
                magnet.stage_data(s, 1, autostart=True)
                time_now = magnet.get_time()
                start_time = time_now + field_buffer_time
                end_time = start_time + field_acquisition_time
                # save the data
                inst_grp = pos_grp.create_group('Field sequence' + str(j))

                hallprobe.save(inst_grp, start_time=start_time, end_time=end_time)
                bighallprobe.save(inst_grp, start_time=start_time, end_time=end_time)
                magnet.save(inst_grp, start_time=start_time, end_time=end_time)
    print('Experiment finished')
    set_baseline(moke)
    if not movement_blocked:
        linearstage.set_position([0, 0, 0])
    else:
        linearstage.stop()
    magnet.stage_data(signals.get_const_signal([0, 0, 0]), 1, autostart=True)


def saturation_test(moke):
    set_baseline(moke)

    fields_time = 10
    fields = [
        lambda x: x,
        lambda x: np.zeros(len(x)),
        lambda x: np.zeros(len(x))
    ]

    magnet = moke.instruments['hexapole']
    NI1 = moke.controller['NIcard1']
    NI2 = moke.controller['NIcard2']

    magnet.stop()
    NI1.flush_data()
    magnet.stage_data(fields, fields_time, autostart=True)
    NI1.wait_for_time(fields_time)
    magnet.stop()

    filename = "Saturation_fields" + time.strftime("%Y%m%d-%H%M") + '.h5'
    with h5py.File(filename, 'w') as file:
        result_group = file.create_group('results')
        moke.instruments['hallprobe'].save(
            result_group, period=fields_time, end=False)
    set_baseline(moke)
