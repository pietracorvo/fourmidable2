import sys
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import numpy as np
import warnings
from data.signal_generation import get_const_signal

COLORS = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194),
          (127, 127, 127), (188, 189, 34), (23, 190, 207)]
PENS = [pg.mkPen(c, width=3) for c in COLORS]


class ApplyCustomField(QWidget):

    def __init__(self, moke):
        super().__init__()
        self.setWindowTitle('Apply custom field')
        self.imported_data = None
        self.selected_file = None
        self.moke = moke
        self.hexapole = moke.instruments['hexapole']

        # add apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_button_clicked)
        self.apply_button.setEnabled(False)
        # add import button
        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.openFileNameDialog)
        # add stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_fields)

        # add plot
        self.plot = pg.PlotWidget(title='Signal plot')

        self.openFileNameDialog()

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.import_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.plot)
        self.setLayout(main_layout)

    def openFileNameDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select file", "", "CSV (*.csv)")
        if fileName:
            try:
                data = np.loadtxt(fileName)
                if data.shape[1] == 4 and len(data.shape) == 2:
                    self.imported_data = data
                    self.selected_file = fileName
                    self.plot_data()
                    self.apply_button.setEnabled(True)
            except:
                warnings.warn('Valid file not selected')

    def plot_data(self):
        """Plots the selected data"""

        self.plot.setLabel('bottom', 't')
        self.plot.setLabel('left', 'Fields')
        clear = True
        names = ['x', 'y', 'z']
        for i in range(3):
            self.plot.plot(self.imported_data[:, 0], self.imported_data[:, i + 1], clear=clear, pen=PENS[i],
                           name=names[i])
            clear = False

    def apply_button_clicked(self):
        """Applies the selected field"""
        t = self.imported_data[:, 0]
        signal = self.imported_data[:, 1:]
        self.hexapole.stage_interp(t, signal)

    def stop_fields(self):
        """Applies 0s to the field values"""
        values = [0] * 3
        self.hexapole.stage_data(get_const_signal(values), 1)


if __name__ == '__main__':
    qApp = QApplication(sys.argv)
    aw = ApplyCustomField(1)

    aw.show()
    qApp.exec_()
