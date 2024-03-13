from inspect import getmembers, isfunction, ismethod
from PyQt5.QtWidgets import *
import experiments
from PyQt5.QtCore import QThread, pyqtSignal
import control.exceptions as myexceptions
import traceback

# TODO: think of  a way to gracefully close the experiment
class ExperimentThread(QThread):
    signal = pyqtSignal()

    def __init__(self, moke, get_selected_experiment):
        QThread.__init__(self)
        self.moke = moke
        self.get_selected_experiment = get_selected_experiment  # function handle
        self.experiment_vars = []

    # run method gets called when we start the thread
    def run(self):
        exp = self.get_selected_experiment()
        try:
            exp(self.moke)
        except:
            traceback.print_exc()
            self.moke.stop("outputs")
        self.signal.emit()

class ExperimentSelector(QWidget):
    def __init__(self, moke):
        self.moke = moke
        QWidget.__init__(self)

        # add a group box containing controls
        self.experiment_box = QGroupBox("Experiment selector")

        # get a list of all of the experiments
        self.experiment_list = getmembers(experiments, isfunction) + getmembers(experiments, ismethod)
        self.combobox = QComboBox(self)
        for e in self.experiment_list:
            self.combobox.addItem(e[0])

        # experiment window list for experiments which are widgets
        self.experiment_window_list = []

        start_button = QPushButton("Start experiment")
        start_button.clicked.connect(self.start_experiment_clicked)
        self._experiment_thread = ExperimentThread(self.moke, self.get_selected_experiment)
        self._experiment_thread.signal.connect(self.experiment_finished)

        stop_experiment = QPushButton("Stop")
        stop_experiment.clicked.connect(self.stop_clicked)

        # set layout
        layout = QVBoxLayout()
        layout.addWidget(self.combobox)
        layout.addWidget(start_button)
        layout.addWidget(stop_experiment)

        self.experiment_box.setLayout(layout)
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.experiment_box)
        self.setLayout(main_layout)
        self.setMaximumHeight(400)

    def start_experiment_clicked(self):
        exp = self.get_selected_experiment()
        if isinstance(exp, QWidget):
            aw = exp(self.moke)
            aw.show()
            self.experiment_window_list.append(aw)
        else:
            self._experiment_thread.start()

    def stop_clicked(self):
        if self._experiment_thread.isRunning():
            self._experiment_thread.terminate()
        self.moke.stop(err="outputs")

    def experiment_finished(self):
        '''Trigger called when the experiment is finished'''
        pass

    def get_selected_experiment(self):
        index = self.combobox.currentIndex()
        return self.experiment_list[index][1]

    def fileQuit(self):
        self._experiment_thread.terminate()
        self.moke.stop()
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()


if __name__ == '__main__':
    import sys
    from control.instruments.moke import Moke
    import gui.exception_handling
    with Moke() as moke:
        app = QApplication(sys.argv)
        aw = ExperimentSelector(moke)
        aw.show()
        qApp.exec_()
