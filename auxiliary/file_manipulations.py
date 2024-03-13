import os
import time


def create_safe_filename(file_name, ext=None):
    # first ensure correct extension
    if ext is not None and os.path.splitext(file_name)[1] != ext:
        file_name = os.path.splitext(file_name)[0] + ext

    if os.path.isfile(file_name):
        expand = 0
        while True:
            new_file_name = os.path.splitext(
                file_name)[0] + '_{:04}'.format(expand) + os.path.splitext(file_name)[1]
            if os.path.isfile(new_file_name):
                expand += 1
                continue
            else:
                file_name = new_file_name
                break
        return new_file_name
    else:
        return file_name


def get_datetimestr():
    return time.strftime("%Y%m%d-%H%M%S")


def append_datetimestr(file_name):
    splitext = os.path.splitext(file_name)
    datetimetxt = get_datetimestr()
    return splitext[0] + '_' + datetimetxt + splitext[1]
