from pipython import GCSDevice


class PIcontrol(GCSDevice):
    def __init__(self, serialnum='416003837', device_name='E-873', name=''):
        """Initialises the PI controller and connects to the usb port"""
        GCSDevice.__init__(self, device_name)
        self.name = name
        self.ConnectUSB(serialnum)

    def stop(self):
        """Function to stop the device after which it should be safe to delete"""
        try:
            self.STP()
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
