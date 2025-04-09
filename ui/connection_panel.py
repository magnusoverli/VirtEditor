from PyQt6.QtWidgets import (QGroupBox, QGridLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QHBoxLayout, QProgressBar)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from utils.logger import logger

class ConnectionPanel(QGroupBox):
    """Widget for connection settings"""
    
    connectionRequested = pyqtSignal(str, str, str)  # ip, username, password - no slot needed initially
    refreshDataRequested = pyqtSignal()  # Signal to refresh data for current slot
    allSlotsRequested = pyqtSignal()  # Signal to fetch data for all slots
    
    def __init__(self, parent=None):
        super().__init__("Connection Settings", parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        layout = QGridLayout()
        self.setLayout(layout)
        
        # IP address
        layout.addWidget(QLabel("Device IP:"), 0, 0)
        self.ip_edit = QLineEdit("10.51.128.92")  # Default IP
        layout.addWidget(self.ip_edit, 0, 1)
        
        # Slot selection
        layout.addWidget(QLabel("Slot:"), 0, 2)
        self.slot_combo = QComboBox()
        # Start with an empty dropdown - will be populated after connection
        self.slot_combo.setEnabled(False)
        # Set placeholder text properly (this doesn't add an item)
        self.slot_combo.setPlaceholderText("No slots detected")
        # Connect the slot change signal to refresh data
        self.slot_combo.currentIndexChanged.connect(self.on_slot_changed)
        layout.addWidget(self.slot_combo, 0, 3)
        
        # Username and password
        layout.addWidget(QLabel("Username:"), 1, 0)
        self.username_edit = QLineEdit("admin")  # Default username
        layout.addWidget(self.username_edit, 1, 1)
        
        layout.addWidget(QLabel("Password:"), 1, 2)
        self.password_edit = QLineEdit("admin")  # Default password
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit, 1, 3)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar, 2, 0, 1, 4)
        
        # Connection buttons
        button_layout = QHBoxLayout()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.request_connection)
        button_layout.addWidget(self.connect_button)
        
        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.on_refresh_data)
        self.refresh_button.setEnabled(False)  # Disabled until first connection
        button_layout.addWidget(self.refresh_button)
        
        layout.addLayout(button_layout, 1, 4)
        
        # Connection status
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status, 0, 4)
    
    def request_connection(self):
        """Emit signal to request initial connection"""
        ip = self.ip_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()
        
        # Initial connection will trigger slot detection automatically
        self.connectionRequested.emit(ip, username, password)
        
        # Show progress indicator
        self.progress_bar.setVisible(True)
        self.connect_button.setEnabled(False)
        self.connection_status.setText("Connecting...")
        self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
    
    def on_refresh_data(self):
        """Signal to refresh data for current slot"""
        if self.slot_combo.currentText() == "All Slots":
            logger.debug("Refreshing data for all slots")
            self.set_connecting_state()
            self.allSlotsRequested.emit()
        elif self.slot_combo.currentText():
            logger.debug(f"Refreshing data for slot {self.slot_combo.currentText()}")
            self.set_connecting_state()
            self.refreshDataRequested.emit()
    
    def on_slot_changed(self, index):
        """Handle slot selection change"""
        logger.debug(f"Slot selection changed to index {index}, text: {self.slot_combo.currentText()}")
        # Only refresh if index is valid and the combo box is enabled
        if index >= 0 and self.slot_combo.isEnabled() and self.slot_combo.count() > 0:
            selected_slot = self.slot_combo.currentText()
            
            if selected_slot == "All Slots":
                logger.debug("'All Slots' selected, requesting all slots data")
                self.set_connecting_state()
                self.allSlotsRequested.emit()
            elif selected_slot != "No slots detected":
                logger.debug(f"Slot {selected_slot} selected, requesting data")
                self.set_connecting_state()
                self.refreshDataRequested.emit()
    
    def update_slots(self, slots):
        """Update the slot dropdown with detected slots"""
        logger.debug(f"Updating slots dropdown with: {slots}")
        
        # Hide progress indicator
        self.progress_bar.setVisible(False)
        
        # Block signals during update to prevent triggering slot_changed events
        self.slot_combo.blockSignals(True)
        
        # Clear the combo box completely
        self.slot_combo.clear()
        
        if slots:
            logger.debug(f"Adding {len(slots)} slots to dropdown")
            
            # Add "All Slots" option as the first item
            self.slot_combo.addItem("All Slots")
            
            # Add all detected slots
            for slot in slots:
                self.slot_combo.addItem(str(slot))
            
            # Enable the slot dropdown and refresh button
            self.slot_combo.setEnabled(True)
            self.refresh_button.setEnabled(True)
            
            # Set to "Connected - Select Slot" state
            self.set_select_slot_state()
            
            # Remove placeholder text as we now have actual items
            self.slot_combo.setPlaceholderText("")
            
            # Don't automatically select a slot - let the user choose
            logger.debug("Slots populated, ready for user selection")
        else:
            logger.debug("No slots to add to dropdown")
            # If no slots detected, set the placeholder text
            self.slot_combo.setPlaceholderText("No slots detected")
            self.slot_combo.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.connection_status.setText("No slots available")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        
        # Unblock signals
        self.slot_combo.blockSignals(False)

    def set_connecting_state(self):
        """Update UI for connecting state"""
        logger.debug("Setting UI to connecting state")
        self.connect_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.connection_status.setText("Connecting...")
        self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
    
    def set_connected_state(self):
        """Update UI for connected state with active slot"""
        logger.debug("Setting UI to connected state with active slot")
        self.connect_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.connection_status.setText("Connected")
        self.connection_status.setStyleSheet("color: green; font-weight: bold;")
    
    def set_select_slot_state(self):
        """Update UI for connected but waiting for slot selection"""
        logger.debug("Setting UI to 'Connected - Select Slot' state")
        self.connect_button.setEnabled(True)
        self.refresh_button.setEnabled(False)  # Disable until slot is selected
        self.progress_bar.setVisible(False)
        self.connection_status.setText("Connected - Select Slot")
        self.connection_status.setStyleSheet("color: green; font-weight: bold;")
        
        # Highlight the slot dropdown (just set focus, don't open popup)
        self.slot_combo.setFocus()
        # Removed showPopup() to prevent automatic opening
    
    def set_error_state(self):
        """Update UI for error state"""
        logger.debug("Setting UI to error state")
        self.connect_button.setEnabled(True)
        self.refresh_button.setEnabled(self.slot_combo.count() > 0)  # Only if we had slots before
        self.progress_bar.setVisible(False)
        self.connection_status.setText("Connection Failed")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")