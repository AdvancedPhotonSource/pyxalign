"""
Interactive ROI selection widget for 3D arrays.

This module provides tools for interactively selecting rectangular regions
of interest in 3D array data using click-and-drag mouse interaction.
"""

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QApplication,
    QSpinBox,
    QGroupBox,
    QGridLayout,
)

from pyxalign.api.options.roi import ROIOptions
from pyxalign.interactions.viewers.base import ArrayViewer
from pyxalign.interactions.utils.misc import switch_to_matplotlib_qt_backend


class ROISelector(QWidget):
    """
    Interactive widget for selecting rectangular regions of interest in 3D arrays.
    
    The ROI is shared across all frames of the 3D array and parameterized by
    center coordinates and extents in pixel units.
    
    Signals
    -------
    roi_changed : ROIOptions
        Emitted when ROI parameters change, containing updated ROIOptions object.
    """
    
    roi_changed = pyqtSignal(object)  # Will emit ROIOptions object
    
    def __init__(
        self, 
        array3d: np.ndarray, 
        roi_options: Optional[ROIOptions] = None, 
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the ROI selector widget.
        
        Args:
            array3d: 3D numpy array to display and select ROI from
            roi_options: Optional ROI configuration. If None, uses default values.
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Store array and validate
        if array3d is None:
            raise ValueError("array3d cannot be None")
        if array3d.ndim != 3:
            raise ValueError(f"array3d must be 3-dimensional, got {array3d.ndim}D")
        
        self.array3d = array3d
        
        # Use provided options or create default
        if roi_options is None:
            self.roi_options = ROIOptions()
        else:
            self.roi_options = roi_options
        
        # Initialize ArrayViewer
        self.array_viewer = ArrayViewer(array3d)
        
        # Initialize ROI graphics item and spinboxes
        self.roi_item = None
        self.spinboxes = {}
        self._updating_from_graphics = False  # Flag to prevent recursive updates
        
        # Setup UI and ROI graphics
        self.setup_ui()
        self.setup_roi_graphics()
        
        # Set window properties
        self.setWindowTitle("ROI Selector")
        self.resize(900, 750)
    
    def setup_ui(self):
        """Setup the widget layout."""
        layout = QVBoxLayout()
        
        # Main array viewer with ROI overlay
        layout.addWidget(self.array_viewer)
        
        # ROI parameter display
        roi_info = self.create_roi_info_display()
        layout.addWidget(roi_info)
        
        self.setLayout(layout)
    
    def create_roi_info_display(self):
        """Create ROI parameter controls with spinboxes for each attribute."""
        # Create group box for ROI controls
        roi_group = QGroupBox("ROI Parameters")
        roi_group.setStyleSheet("QGroupBox { font-size: 13pt; font-weight: bold; }")
        
        # Create grid layout for organized parameter display
        grid_layout = QGridLayout()
        
        # Set reasonable ranges based on array dimensions
        max_x = self.array3d.shape[2]
        max_y = self.array3d.shape[1]
        
        # Create spinboxes for each ROI parameter
        self.spinboxes = {}
        
        # Horizontal offset (center X)
        grid_layout.addWidget(QLabel("Horizontal Offset (Center X):"), 0, 0)
        self.spinboxes['horizontal_offset'] = QSpinBox()
        self.spinboxes['horizontal_offset'].setRange(0, max_x)
        self.spinboxes['horizontal_offset'].setValue(self.roi_options.rectangle.horizontal_offset)
        self.spinboxes['horizontal_offset'].valueChanged.connect(self.on_spinbox_changed)
        grid_layout.addWidget(self.spinboxes['horizontal_offset'], 0, 1)
        
        # Vertical offset (center Y)
        grid_layout.addWidget(QLabel("Vertical Offset (Center Y):"), 1, 0)
        self.spinboxes['vertical_offset'] = QSpinBox()
        self.spinboxes['vertical_offset'].setRange(0, max_y)
        self.spinboxes['vertical_offset'].setValue(self.roi_options.rectangle.vertical_offset)
        self.spinboxes['vertical_offset'].valueChanged.connect(self.on_spinbox_changed)
        grid_layout.addWidget(self.spinboxes['vertical_offset'], 1, 1)
        
        # Horizontal range (width)
        grid_layout.addWidget(QLabel("Horizontal Range (Width):"), 0, 2)
        self.spinboxes['horizontal_range'] = QSpinBox()
        self.spinboxes['horizontal_range'].setRange(1, max_x)
        self.spinboxes['horizontal_range'].setValue(self.roi_options.rectangle.horizontal_range)
        self.spinboxes['horizontal_range'].valueChanged.connect(self.on_spinbox_changed)
        grid_layout.addWidget(self.spinboxes['horizontal_range'], 0, 3)
        
        # Vertical range (height)
        grid_layout.addWidget(QLabel("Vertical Range (Height):"), 1, 2)
        self.spinboxes['vertical_range'] = QSpinBox()
        self.spinboxes['vertical_range'].setRange(1, max_y)
        self.spinboxes['vertical_range'].setValue(self.roi_options.rectangle.vertical_range)
        self.spinboxes['vertical_range'].valueChanged.connect(self.on_spinbox_changed)
        grid_layout.addWidget(self.spinboxes['vertical_range'], 1, 3)
        
        # Style the spinboxes
        for spinbox in self.spinboxes.values():
            spinbox.setStyleSheet("QSpinBox { font-size: 12pt; }")
            spinbox.setMinimumWidth(80)
        
        # Style the labels
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            if item and isinstance(item.widget(), QLabel):
                item.widget().setStyleSheet("QLabel { font-size: 12pt; }")
        
        roi_group.setLayout(grid_layout)
        return roi_group
    
    def setup_roi_graphics(self):
        """Initialize the pyqtgraph ROI item with parameters from roi_options."""
        rect_opts = self.roi_options.rectangle
        
        # Handle default values (0) by setting reasonable defaults based on array size
        if rect_opts.horizontal_range == 0 or rect_opts.vertical_range == 0:
            # Set default size to 1/4 of the image dimensions
            default_width = max(50, self.array3d.shape[2] // 4)
            default_height = max(50, self.array3d.shape[1] // 4)
            
            if rect_opts.horizontal_range == 0:
                rect_opts.horizontal_range = default_width
            if rect_opts.vertical_range == 0:
                rect_opts.vertical_range = default_height
        
        # Handle default center position (0,0) by centering in the image
        if rect_opts.horizontal_offset == 0 and rect_opts.vertical_offset == 0:
            rect_opts.horizontal_offset = self.array3d.shape[2] // 2
            rect_opts.vertical_offset = self.array3d.shape[1] // 2
        
        # Convert from center/extent to position/size for pg.RectROI
        # pg.RectROI expects [x, y] position (top-left) and [width, height] size
        pos_x = rect_opts.horizontal_offset - rect_opts.horizontal_range // 2
        pos_y = rect_opts.vertical_offset - rect_opts.vertical_range // 2
        
        self.roi_item = pg.RectROI(
            pos=[pos_x, pos_y], 
            size=[rect_opts.horizontal_range, rect_opts.vertical_range],
            pen=pg.mkPen(color='r', width=2)  # Red outline, 2px width
        )
        
        # Add to the ArrayViewer's plot
        self.array_viewer.plot_item.addItem(self.roi_item)
        
        # Connect ROI change signal
        self.roi_item.sigRegionChanged.connect(self.on_roi_changed)
        
        # Initial update of spinboxes to match the ROI
        self.update_spinboxes_from_roi()
    
    def on_roi_changed(self):
        """Update ROIOptions when user modifies ROI graphics item."""
        if self._updating_from_graphics:
            return
            
        self._updating_from_graphics = True
        
        pos = self.roi_item.pos()
        size = self.roi_item.size()
        
        # Convert from position/size back to center/extent
        center_x = int(pos[0] + size[0] / 2)
        center_y = int(pos[1] + size[1] / 2)
        extent_x = int(size[0])
        extent_y = int(size[1])
        
        # Update the ROIOptions object
        self.roi_options.rectangle.horizontal_offset = center_x
        self.roi_options.rectangle.vertical_offset = center_y
        self.roi_options.rectangle.horizontal_range = extent_x
        self.roi_options.rectangle.vertical_range = extent_y
        
        # Update the spinboxes without triggering their signals
        self.update_spinboxes_from_roi()
        
        # Emit the updated options
        self.roi_changed.emit(self.roi_options)
        
        self._updating_from_graphics = False
    
    def on_spinbox_changed(self):
        """Update ROI graphics when user modifies spinbox values."""
        if self._updating_from_graphics:
            return
        
        # Update ROI options from spinbox values
        self.roi_options.rectangle.horizontal_offset = self.spinboxes['horizontal_offset'].value()
        self.roi_options.rectangle.vertical_offset = self.spinboxes['vertical_offset'].value()
        self.roi_options.rectangle.horizontal_range = self.spinboxes['horizontal_range'].value()
        self.roi_options.rectangle.vertical_range = self.spinboxes['vertical_range'].value()
        
        # Update the graphics item
        self.update_roi_graphics_from_options()
        
        # Emit the updated options
        self.roi_changed.emit(self.roi_options)
    
    def update_spinboxes_from_roi(self):
        """Update spinbox values from current ROI options without triggering signals."""
        rect = self.roi_options.rectangle
        
        # Temporarily block signals to prevent recursive updates
        for spinbox in self.spinboxes.values():
            spinbox.blockSignals(True)
        
        self.spinboxes['horizontal_offset'].setValue(rect.horizontal_offset)
        self.spinboxes['vertical_offset'].setValue(rect.vertical_offset)
        self.spinboxes['horizontal_range'].setValue(rect.horizontal_range)
        self.spinboxes['vertical_range'].setValue(rect.vertical_range)
        
        # Re-enable signals
        for spinbox in self.spinboxes.values():
            spinbox.blockSignals(False)
    
    def update_roi_graphics_from_options(self):
        """Update the ROI graphics item from current ROI options."""
        rect_opts = self.roi_options.rectangle
        pos_x = rect_opts.horizontal_offset - rect_opts.horizontal_range // 2
        pos_y = rect_opts.vertical_offset - rect_opts.vertical_range // 2
        
        # Temporarily disconnect signal to avoid recursive updates
        self.roi_item.sigRegionChanged.disconnect(self.on_roi_changed)
        
        # Update ROI item
        self.roi_item.setPos([pos_x, pos_y])
        self.roi_item.setSize([rect_opts.horizontal_range, rect_opts.vertical_range])
        
        # Reconnect signal
        self.roi_item.sigRegionChanged.connect(self.on_roi_changed)
    
    def get_roi_options(self) -> ROIOptions:
        """
        Get the current ROI options.
        
        Returns:
            Current ROIOptions object with updated parameters
        """
        return self.roi_options
    
    def set_roi_options(self, roi_options: ROIOptions):
        """
        Set new ROI options and update the display.
        
        Args:
            roi_options: New ROI configuration to apply
        """
        self.roi_options = roi_options
        
        # Update the graphics item
        rect_opts = self.roi_options.rectangle
        pos_x = rect_opts.horizontal_offset - rect_opts.horizontal_range // 2
        pos_y = rect_opts.vertical_offset - rect_opts.vertical_range // 2
        
        # Temporarily disconnect signal to avoid recursive updates
        self.roi_item.sigRegionChanged.disconnect(self.on_roi_changed)
        
        # Update ROI item
        self.roi_item.setPos([pos_x, pos_y])
        self.roi_item.setSize([rect_opts.horizontal_range, rect_opts.vertical_range])
        
        # Reconnect signal
        self.roi_item.sigRegionChanged.connect(self.on_roi_changed)
        
        # Update spinboxes
        self.update_spinboxes_from_roi()
        
        # Emit change signal
        self.roi_changed.emit(self.roi_options)


@switch_to_matplotlib_qt_backend
def launch_roi_selector(
    array3d: np.ndarray,
    roi_options: Optional[ROIOptions] = None,
    wait_until_closed: bool = False,
) -> ROISelector:
    """
    Launch the ROI selector GUI for interactively selecting regions of interest.
    
    Args:
        array3d: 3D numpy array to display and select ROI from
        roi_options: Optional ROI configuration. If None, uses default values.
        wait_until_closed: If True, blocks until the GUI window is closed
        
    Returns:
        ROISelector widget instance
        
    Example:
        Launch ROI selector for a 3D array::
        
            roi_widget = launch_roi_selector(my_3d_array)
            roi_widget.roi_changed.connect(lambda opts: print(f"ROI: {opts.rectangle}"))
    """
    app = QApplication.instance() or QApplication([])
    gui = ROISelector(array3d, roi_options)
    gui.setAttribute(Qt.WA_DeleteOnClose)
    gui.show()
    if wait_until_closed:
        app.exec_()
    return gui
