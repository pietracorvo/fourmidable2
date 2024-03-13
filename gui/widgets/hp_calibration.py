from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtProperty, pyqtSignal, QThread
from PyQt5 import QtCore, QtWidgets

import numpy as np
import hjson
import copy

import sys
import os
sys.path.append(os.getcwd())
from experiments.calibration.hallprobe_calibration import calibrate_hallprobe
import pyqtgraph as pg
import pandas as pd


COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class CalibrationThread(QThread):
    signal = pyqtSignal()

    def __init__(self, moke):
        QThread.__init__(self)
        self.moke = moke
        self.result = None
        self.pred = None
        self.data = None

    # run method gets called when we start the thread
    def run(self):
        self.result, self.pred, self.data = calibrate_hallprobe(self.moke)
        self.signal.emit()


class HPCalibration(QtWidgets.QWizard):
    sigCalibrationChanged = pyqtSignal()

    def __init__(self, moke, parent=None):
        super(HPCalibration, self).__init__(parent)
        self.moke = moke
        self.hallprobe = moke.instruments['hallprobe']
        self.initial_calibration = self.hallprobe.calibration

        self.finished_normally = False
        self.button(QtWidgets.QWizard.NextButton).clicked.connect(
            self.next_pressed)
        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(
            self.finish_pressed)
        self.setOption(QtWidgets.QWizard.NoCancelButton)

        self.result = None
        self.calibration_thread = CalibrationThread(self.moke)
        self.calibration_thread.signal.connect(self.calibration_finished)
        self.plots = None

        self.addPage(Page1(self))
        self.addPage(Page2(self))
        self.setWindowTitle("Hallprobe calibration wizard")

    def closeEvent(self, ce):
        self.apply_calculated_calibration()
        if self.plots is not None:
            try:
                self.plots.close()
            except:
                pass
        self.close()

    def apply_calculated_calibration(self):
        if self.finished_normally and self.result is not None:
            new_calibration = self.initial_calibration
            new_calibration.scale = self.result['coefficients']
            self.hallprobe.calibration = new_calibration
            self.sigCalibrationChanged.emit()
        else:
            self.hallprobe.calibration = self.initial_calibration
            self.sigCalibrationChanged.emit()

    def calibration_finished(self):
        result, pred, data = self.calibration_thread.result, self.calibration_thread.pred, self.calibration_thread.data
        self.page(1).result = result
        self.page(1).initializePage()

        # plot the result
        self.plots = plot_result(pred, data)

    def finish_pressed(self):
        self.finished_normally = True
        self.apply_calculated_calibration()
        if self.plots is not None:
            try:
                self.plots.close()
            except:
                pass

    def next_pressed(self):
        print(self.currentId())
        if self.currentId() == 1:
            self.calibration_thread.start()


class Page1(QtWidgets.QWizardPage):
    "Align the lenses and set the calibration to default"

    def __init__(self, parent=None):
        super(Page1, self).__init__(parent)
        self.label1 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.NextButton, 'Start')

    def initializePage(self):
        self.label1.setText(
            """Press Start to start the calibration.""")


class Page2(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(Page2, self).__init__(parent)
        self.result = None

        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        self.label3 = QtWidgets.QLabel()
        self.label4 = QtWidgets.QLabel()
        self.label5 = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        layout.addWidget(self.label3)
        layout.addWidget(self.label4)
        layout.addWidget(self.label5)
        self.setLayout(layout)
        self.setButtonText(QtWidgets.QWizard.FinishButton,
                           'Apply')

    def isComplete(self):
        if self.result is None:
            return False
        else:
            return True

    def initializePage(self):
        self.completeChanged.emit()
        if self.result is not None:
            self.label1.setText(
                'Intercept: {}'.format(self.result['intercept']))
            self.label2.setText(
                'Coefficients: \n{}\n'.format(np.array2string(np.array(self.result['coefficients']), separator=',')))
            self.label3.setText('Score: {}'.format(self.result['score']))

            self.label4.setText("Pressing finish will apply this calibration")
            self.label5.setText(
                "For future use, put the above numbers in settings")
        else:
            self.label1.setText('Calibration running...')


def plot_result(pred, data):
    t = data[:, 0]
    hp = data[:, 1:4]
    bighp = data[:, 4:]
    err = bighp - pred
    stdev = np.std(err)
    win = pg.GraphicsWindow(title="Calibration result")
    # compare the fields

    plt1 = win.addPlot(title='Comparison of predicted vs real fields')
    plt1.addLegend()
    plt1.plot(t, bighp[:, 1], name='big hallprobe', pen=PENS[0])
    plt1.plot(t, pred[:, 1], name='small hallprobes', pen=PENS[1])
    plt1.setLabel('bottom', 't [s]')
    plt1.setLabel('left', 'Bx [mT]')

    # show the errors
    relative_err = bighp - pred
    win.nextRow()
    plt2 = win.addPlot(title='Error in the prediction')
    plt2.plot(t, relative_err[:, 0], pen=PENS[0])
    plt2.setLabel('bottom', 't [s]')
    plt2.setLabel('left', 'Error [mT]')

    # calculate the relative error after binning
    nbins = 100  # number of bins per second

    mn = np.min(t)
    mx = np.max(t)
    bins = np.linspace(mn, mx, np.round(
        (mx - mn) * 1000 / nbins).astype(int))
    data = pd.DataFrame({"t": t, "err": relative_err[:, 0]})
    data['bins'] = pd.cut(data['t'], bins=bins, right=False)
    data = data.groupby('bins').mean().reset_index()
    data.dropna(inplace=True)

    win.nextRow()
    plt3 = win.addPlot(
        title='Error in the prediction, filtered (n_bins= {})'.format(nbins))
    plt3.plot(data["t"], data["err"], pen=PENS[0])
    plt3.setLabel('bottom', 't [s]')
    plt3.setLabel('left', 'Error [mT]')
    return win


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    # wizard = HPCalibration(0)

    # pred = np.random.rand(100, 3)
    # data = np.random.rand(100, 7)
    # win = plot_result(pred, data)
    from control.instruments.moke import Moke

    with Moke() as moke:
        wizard = HPCalibration(moke)
        wizard.show()
        sys.exit(app.exec_())
