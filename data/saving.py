from control.instruments.basic import Instrument
import threading
import h5py
import copy

class MokeSaver(h5py.File):
    def __init__(self, filename, mode='w'):
        super().__init__(filename, mode)
        self.saving_lock = threading.Lock()
        self.save_thread = threading.Thread()
        self.save_lock = threading.Lock()
        self.instruments_to_save = []
        self.groups_to_save = []
        self.args_to_save = []
        self.kwargs_to_save = []

    def save_instruments(self, instruments, group, *args, block=True, **kwargs):
        assert isinstance(instruments, Instrument)
        self.instruments_to_save.append(instruments)
        self.groups_to_save.append(group)
        self.args_to_save.append(args)
        self.kwargs_to_save.append(kwargs)
        # print(len(self.instruments_to_save))

        if not self.save_thread.is_alive():
            self.save_thread = threading.Thread(target=self.save_worker)
            self.save_thread.start()
        if block:
            self.save_thread.join()

    def save_worker(self):
        while len(self.instruments_to_save) != 0:
            inst = self.instruments_to_save.pop(0)
            grp = self.groups_to_save.pop(0)
            args = self.args_to_save.pop(0)
            kwargs = self.kwargs_to_save.pop(0)
            inst.save(grp, *args, **kwargs)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.save_thread.is_alive():
            self.save_thread.join()
        self.close()
        super().__exit__(exc_type, exc_val, exc_tb)

    def __del__(self):
        try:
            if self.save_thread.is_alive():
                self.save_thread.join()
        except:
            pass
        try:
            self.close()
        except:
            pass
