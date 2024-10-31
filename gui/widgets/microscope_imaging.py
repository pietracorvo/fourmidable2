import sys
from PyQt5.QtWidgets import *
import pyqtgraph as pg
from display.instrument_plotting import *
from PyQt5.QtCore import QTimer
import threading

class ImagingWidget(QWidget):
    def __init__(self, gui, data_folder=''):
        super().__init__()
        self.gui = gui
        self.name = 'hamamatsu_camera'
        self.gui.toggle_view(self.name, False)
        self.setWindowTitle('Kerr microscope - Imaging Experiment ')
        self.moke = self.gui.moke
        self.stop_event = threading.Event()

        # Create two views: one for live view and one for last frame
        self.live_view = pg.GraphicsLayoutWidget()  # Left: Live view
        self.last_frame_view = pg.GraphicsLayoutWidget()  # Right: Last frame view

        # Start the camera acquisition
        self.moke.instruments[self.name].start_acquisition()

        # Live camera plot (left)
        self.liveview = CameraLivePlotting(self.moke, view=self.live_view)

        # Last frame plot (right)
        self.last_frame_viewer = CameraStaticPlotting(self.moke.instruments[self.name], view=self.last_frame_view)
        self.last_frame_data = None  # Store the last acquired frame

        # Timer for live updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_live_plot)  # Only update the live view continuously

        # Button to update the last frame plot
        #self.update_button = QPushButton('Update Last Frame')
        self.last_frame_viewer.photo_button.clicked.connect(self.update_last_frame)

        # Layout to position both plots side by side
        layout = QHBoxLayout()

        # Sub-layout for the live view and last frame
        plot_layout = QHBoxLayout()
        # Add the menu (right)
        plot_layout.addWidget(self.liveview.get_menu_widget())
        plot_layout.addWidget(self.live_view)  # Add live view to the layout (left)
        plot_layout.addWidget(self.last_frame_viewer.get_menu_widget())
        plot_layout.addWidget(self.last_frame_view)  # Add last frame view to the layout (right)

        # Main layout includes both plots and the button below
        main_layout = QVBoxLayout()
        main_layout.addLayout(plot_layout)  # Add plots (top)
        # main_layout.addWidget(self.update_button)  # Add the update button (bottom)

        self.setLayout(main_layout)

        # Start the timer to update the live plot periodically
        self.start_timer()

    def update_live_plot(self):
        """Update the live plot (left side) continuously."""
        self.liveview.plot()

    def update_last_frame(self):
        """Update the right-hand plot with the last captured frame when button is clicked."""
        self.last_frame_data = self.liveview.get_plot_data()  # Get the current frame data

        if self.last_frame_data is not None:
            self.last_frame_viewer.image.setImage(
                self.last_frame_data, axisOrder='row-major', autoDownsample=False, border=(169, 169, 169)
            )

    def start_timer(self):
        """Start the timer with the desired frame rate for the live plot."""
        self.timer.start(50)  # Set timer interval to 50 ms (~20 fps)

    def closeEvent(self, event):
        """Handle widget close event by stopping the timer and closing the widget."""
        self.timer.stop()
        self.close()
