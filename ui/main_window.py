import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMessageBox, QLabel)

from ui.connection_panel import ConnectionPanel
from ui.info_display import InfoDisplay
from ui.log_viewer import LogViewer
from api.client import DeviceApiClient
from api.worker import ApiWorker, SlotDetectionWorker
from models.device_data import DeviceData
from utils.logger import logger

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Configuration")
        self.setMinimumSize(800, 600)
        
        # Set up UI components
        self.setup_ui()
        
        # Initialize API-related attributes
        self.api_client = None
        self.worker = None
        self.slot_detection_worker = None
        
        # Store the last successful connection parameters
        self.last_ip = ""
        self.last_slot = ""
        self.last_username = ""
        self.last_password = ""
        
        # Log viewer dialog
        self.log_viewer = None

        # Store the connection state
        self.is_connected = False

        logger.info("Main window initialized")
    
    def setup_ui(self):
        """Set up the UI components"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.setup_menu_bar()
        
        # Connection panel
        self.connection_panel = ConnectionPanel()
        self.connection_panel.connectionRequested.connect(self.initial_connection)
        self.connection_panel.refreshDataRequested.connect(self.refresh_current_slot)
        main_layout.addWidget(self.connection_panel)
        
        # Information display
        self.info_display = InfoDisplay()
        main_layout.addWidget(self.info_display, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def setup_menu_bar(self):
        """Set up the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Log viewer action
        log_viewer_action = file_menu.addAction("View &Logs")
        log_viewer_action.triggered.connect(self.show_log_viewer)
        
        # Exit action
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.close)
    
    def show_log_viewer(self):
        """Show the log viewer dialog"""
        if self.log_viewer is None:
            self.log_viewer = LogViewer(self)
        
        self.log_viewer.show()
        self.log_viewer.raise_()
        self.log_viewer.activateWindow()
        
        logger.info("Log viewer opened")

    def initial_connection(self, ip, username, password):
        """Handle the initial connection and slot detection"""
        logger.info(f"Initial connection to {ip}")
        
        # Create or update API client
        self.api_client = DeviceApiClient(ip, username, password)
        logger.info(f"Created new API client for {ip}")
        
        # Store the credentials
        self.last_ip = ip
        self.last_username = username
        self.last_password = password
        
        # First detect available slots
        self.detect_slots(ip, username, password)

    def refresh_data(self, ip, slot, username, password):
        """Refresh data for a specific slot"""
        logger.info(f"Refreshing data for slot {slot}")
        self.fetch_data(ip, slot, username, password)

    def refresh_current_slot(self):
        """Refresh data for the currently selected slot"""
        slot = self.connection_panel.slot_combo.currentText()
        if slot:
            logger.info(f"Refreshing data for slot {slot}")
            self.fetch_data(self.last_ip, slot, self.last_username, self.last_password)
        else:
            logger.warning("Attempted to refresh data but no slot is selected")
            self.connection_panel.set_error_state()

    
    def on_worker_finished(self):
        """Called when the worker thread finishes"""
        if hasattr(self, 'worker') and self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
    
    def display_data(self, data):
        """Display the fetched data"""
        self.statusBar().showMessage("Connected")
        self.connection_panel.set_connected_state()
        
        # Store successful connection parameters
        self.last_ip = self.connection_panel.ip_edit.text()
        self.last_slot = self.connection_panel.slot_combo.currentText()
        self.last_username = self.connection_panel.username_edit.text()
        self.last_password = self.connection_panel.password_edit.text()
        
        logger.info(f"Successfully connected to {self.last_ip}, slot {self.last_slot}")
        
        # Create data model and update display
        try:
            device_data = DeviceData(data)
            self.info_display.update_display(device_data)
            
            # Log basic device info
            if device_data.product_info:
                logger.info(f"Device: {device_data.product_info.get('prodname', 'N/A')}, "
                        f"Serial: {device_data.product_info.get('serialfull', 'N/A')}, "
                        f"SW: {device_data.product_info.get('swver', 'N/A')}")
            
            # Log alarm counts
            if device_data.alarm_info:
                logger.info(f"Alarms: {device_data.alarm_info.get('n_total', 0)} total, "
                        f"{device_data.alarm_info.get('n_critical', 0)} critical, "
                        f"{device_data.alarm_info.get('n_major', 0)} major")
                
                # Log warnings if there are critical alarms
                if device_data.alarm_info.get('n_critical', 0) > 0:
                    logger.warning(f"Device has {device_data.alarm_info.get('n_critical', 0)} critical alarms!")
        
        except Exception as e:
            logger.error(f"Error processing device data: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Error processing device data: {str(e)}")
    
    def handle_error(self, error_msg):
        """Handle API errors"""
        self.statusBar().showMessage("Error")
        self.connection_panel.set_error_state()
        
        logger.error(f"API error: {error_msg}")
        
        # Refresh button only enabled if we had a successful connection before
        if self.last_ip:
            self.connection_panel.refresh_button.setEnabled(True)
        
        QMessageBox.critical(self, "API Error", error_msg)
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.log_viewer:
            self.log_viewer.close()
        
        logger.info("Application closing")
        event.accept()

    def detect_slots(self, ip, username, password):
        """Detect available slots in the device"""
        logger.info(f"Starting slot detection for {ip}")
        
        # Create or update API client if needed
        if (self.api_client is None or
            ip != self.last_ip or
            username != self.last_username or
            password != self.last_password):
            self.api_client = DeviceApiClient(ip, username, password)
            logger.info(f"Created new API client for {ip}")
        
        self.statusBar().showMessage("Detecting slots...")
        
        # Create worker thread for slot detection
        self.slot_detection_worker = SlotDetectionWorker(self.api_client)
        self.slot_detection_worker.slotsDetected.connect(self.handle_detected_slots)
        self.slot_detection_worker.error.connect(self.handle_slot_detection_error)
        self.slot_detection_worker.finished.connect(self.on_slot_detection_finished)
        self.slot_detection_worker.start()

    def handle_detected_slots(self, slots):
        """Handle the list of detected slots"""
        if slots:
            logger.info(f"Detected {len(slots)} slots: {slots}")
            self.statusBar().showMessage(f"Detected {len(slots)} slots")
            self.is_connected = True
            
            # Update status in footer
            self.footer_label = QLabel(f"Detected {len(slots)} slots")
            self.statusBar().addPermanentWidget(self.footer_label)
            
            # Update the connection panel with slots - this will also update the status
            self.connection_panel.update_slots(slots)
            
            # Auto-select and load the first slot
            if slots and not self.last_slot:
                self.last_slot = str(slots[0])
                self.fetch_data(self.last_ip, self.last_slot, self.last_username, self.last_password)
        else:
            logger.warning("No slots detected")
            self.statusBar().showMessage("No slots detected")
            self.is_connected = False
            
            # Update the connection panel
            self.connection_panel.update_slots([])
            self.connection_panel.set_error_state()

    def handle_slot_detection_error(self, error_msg):
        """Handle errors during slot detection"""
        logger.error(f"Slot detection error: {error_msg}")
        self.statusBar().showMessage("Slot detection failed")
        self.is_connected = False
        
        # Show error message to the user
        QMessageBox.warning(self, "Slot Detection Error", error_msg)
        
        # Update the UI
        self.connection_panel.set_error_state()
        self.connection_panel.update_slots([])  # Clear slots

    def on_slot_detection_finished(self):
        """Clean up after slot detection finishes"""
        if hasattr(self, 'slot_detection_worker') and self.slot_detection_worker is not None:
            self.slot_detection_worker.deleteLater()
            self.slot_detection_worker = None

    def fetch_data(self, ip, slot, username, password):
        """Fetch data from the device API"""
        if not ip:
            logger.warning("Empty IP address provided")
            QMessageBox.warning(self, "Input Error", "Please enter a device IP address.")
            return
        
        if not slot:
            logger.warning("No slot selected")
            QMessageBox.warning(self, "Input Error", "Please select a slot.")
            return
        
        # Create or update API client if connection parameters changed
        if (self.api_client is None or
            ip != self.last_ip or
            username != self.last_username or
            password != self.last_password):
            self.api_client = DeviceApiClient(ip, username, password)
            logger.info(f"Created new API client for {ip}")
        
        self.statusBar().showMessage("Connecting...")
        self.connection_panel.set_connecting_state()
        
        logger.info(f"Attempting to connect to {ip}, slot {slot}")
        
        # Create worker thread to fetch data
        self.worker = ApiWorker(self.api_client, slot)
        self.worker.dataReady.connect(self.display_data)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()
        
        # Store the current slot
        self.last_slot = slot