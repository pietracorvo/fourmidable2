import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pyqtgraph.console
import data
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QObject
import data.signal_generation as signals
import sys
import os
import traceback

# logger class for writing stdout to console as well as the terminal


class SignalLogger(QObject):
    writeSignal = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        self.terminal = sys.stdout

    def write(self, message):
        try:
            self.terminal.write(message)
            self.writeSignal.emit(message)
        except:
            traceback.print_exc()
            sys.stdout = sys.__stdout__

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass


class ConsoleWidget(QWidget):

    def __init__(self, moke):
        self.moke = moke
        QWidget.__init__(self)

        # build an initial namespace for console commands to be executed
        namespace = {'pd': pd,
                     'np': np,
                     'plt': plt,
                     'signals': signals,
                     'data_processing': data,
                     'moke': moke
                     }
        namespace.update(
            {name: inst for name, inst in self.moke.instruments.items()})

        # initial text to display in the console
        text = """
        This is an interactive python console. The numpy, pandas and pyplot modules have already been imported as 'np', 'pg' and 'plt'. 
        All of the instruments are objects with corresponding names. 
        Library of signals is imported under signals module.
        """
        self.console = pyqtgraph.console.ConsoleWidget(
            namespace=namespace, text=text)
        self.console.show()
        self.console.setWindowTitle('ConsoleWidget')

        layout = QHBoxLayout()
        layout.addWidget(self.console)
        self.setLayout(layout)
        # redirect printing to the console
        self.signal_logger = SignalLogger()
        sys.stdout = self.signal_logger
        self.signal_logger.writeSignal.connect(self.console.write)

    def __del__(self):
        sys.stdout = sys.__stdout__

    def closeEvent(self, ce):
        sys.stdout = sys.__stdout__
        self.close()


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    import gui.exception_handling

    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = ConsoleWidget(moke)
        aw.show()
        qApp.exec_()
