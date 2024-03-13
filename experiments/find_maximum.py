import numpy as np
import time


def get_woll_signal(woll, time_increment=0.2, delay=0.2):
    "Gets the mean wollaston signal during the last time_increment"
    start_time = woll.get_time() + delay
    signal = woll.get_data(start_time=start_time,
                           end_time=start_time + time_increment)

    #Detector arm for "auto-find the maximum"
    signal_out = np.mean((signal['det2']).values)

    return signal_out


def find_max_direction(stage, woll, distance, step, direction, stop_event=None):
    """Finds the maximum in the given direction with the given step"""
    # have only once chance of reversing
    has_reversed = False
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        if distance < 0:
            break
        # get the reference signal
        ref_signal = get_woll_signal(woll)
        # move
        stage.set_position({direction: step}, relative=True, wait=True)
        # stop the stages after every step to limit the instabilites
        time.sleep(0.1)
        stage.stop()
        # get the signal
        signal = get_woll_signal(woll)

        # if the signal increased, we are going in the correct direction
        if signal > ref_signal:
            distance -= step
            # can no longer reverse
            has_reversed = True
        # otherwise, we are going in the wrong direction, reverse if have not already done so
        elif not has_reversed:
            # move back
            stage.set_position({direction: -step}, relative=True, wait=True)
            # change the movement direction
            step *= -1
            has_reversed = True
        # if we have already reversed and we are not going in the right direction, we are done
        else:
            stage.set_position({direction: -step}, relative=True, wait=True)
            break


def find_maximum(moke, distance=10, start_step=2, end_step=0.5, stop_event=None):
    """Finds the maximum intensity of wollaston signal by moving the stages iteratively.

    Args:
        distance: max distance to move in um
        start_step: initial step to search for maximum in um
        end_step: final step at which to move in um (how fine we want to find the maximum)
    """
    stage = moke.instruments['stage']
    woll = moke.instruments['wollaston2']
    directions_to_search = ['x', 'y']  # , 'z']

    # incrementaly reduce the step until smaller than the end step
    step = start_step
    print('Starting find maximum...')
    while step > end_step:
        for direction in directions_to_search:
            if stop_event is not None and stop_event.is_set():

                return
            find_max_direction(stage, woll, distance, step,
                               direction=direction, stop_event=stop_event)
        # when found the max in all three directions, reduce the step
        step /= 2
    # actively hold the current position
    stage.hold_position()
    print('Found maximum!')
