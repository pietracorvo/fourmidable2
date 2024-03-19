from control.controllers.newport_interface import Controller
import time
productid = 16384
vendorid = 4173

control = Controller(productid, vendorid)
commands = [
            "1>1DH0",
            "1>2DH0",
            "1>3DH0",
            "1>1PA0",
            "1>2PA2000",
            "1>3PA0",
            "1>1DH0",
            "1>2DH1000",
            "1>3DH0",
            "1>1PA0",
            "1>2PR0",
            "1>3PA0"]

motors = ['1>1', '1>2', '1>3']

# run all of the commands
for c in commands:
    print(c)
    control.command(c)
    # wait for the command to finish
    for m in motors:
        while True:
            if int(control.command(m + 'MD?').split('>')[1]):
                break
            time.sleep(0.1)
            print('Waiting')
    print('position: ', control.command('1>2PA?').split('>')[1])
