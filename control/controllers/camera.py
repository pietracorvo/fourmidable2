from instrumental import instrument, list_instruments
import types


# initialises the thorlabs camera controller class as is
def CameraControl(name='', class_name="UC480_Camera", id=None):
    """Gets the Thorlabs camera controller class from the instrumental library.

        Further info on http://instrumental-lib.readthedocs.io/en/stable/cameras.html

        Args:
            name (str): camera name
        Returns:
            camera controller
    """
    paramsets = list_instruments(module='cameras')
    found = False
    for p in paramsets:
        if p['classname'] == class_name and (id is None or p['id']==id):
            found = True
            break
    if not found:
        raise Exception('The camera controller with name ', class_name, ' and id ', id, ' not found')
    cam = instrument(p)
    cam.name = name
    module = type(cam).__module__
    if module.split('.')[2] == 'cameras':
        def stop_fun(c):
            c.stop_live_video()

        def enter(self):
            return self

        def exit(self, *args):
            self.close()

        # add the stop function for compatibility with other controllers, it should just make it safe to delete
        cam.stop = types.MethodType(stop_fun, cam)
        cam.__enter__ = types.MethodType(enter, cam)
        cam.__exit__ = types.MethodType(exit, cam)
        return cam
    else:
        raise ValueError('The provided name did not return a camera object.')
