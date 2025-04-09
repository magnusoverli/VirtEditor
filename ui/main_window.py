import logging
import threading
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMessageBox, 
                           QLabel, QProgressBar, QStatusBar)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer

from ui.connection_panel import ConnectionPanel
from ui.info_display import InfoDisplay
from ui.log_viewer import LogViewer
from api.client import DeviceApiClient
from api.worker import ApiWorker, SlotDetectionWorker
from models.device_data import DeviceData
from utils.logger import logger

class MainWindow(QMainWindow):
    """Main application window"""
    
    # Signal for when all slots data is collected
    all_slots_data_ready = pyqtSignal(dict)
    
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
        self.slot_data_fetcher = None
        
        # Store the last successful connection parameters
        self.last_ip = ""
        self.last_slot = ""
        self.last_username = ""
        self.last_password = ""
        
        # Log viewer dialog
        self.log_viewer = None

        # Store the connection state
        self.is_connected = False
        
        # Store all slots data
        self.all_slots_data = {}
        
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
        self.connection_panel.allSlotsRequested.connect(self.fetch_all_slots_data)
        main_layout.addWidget(self.connection_panel)
        
        # Information display
        self.info_display = InfoDisplay()
        main_layout.addWidget(self.info_display, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Progress bar in status bar for multi-slot operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
    
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

    def refresh_current_slot(self):
        """Refresh data for the currently selected slot"""
        slot = self.connection_panel.slot_combo.currentText()
        if slot and slot != "All Slots":
            logger.info(f"Refreshing data for slot {slot}")
            self.fetch_data(self.last_ip, slot, self.last_username, self.last_password)
        elif slot == "All Slots":
            logger.info("Refreshing data for all slots")
            self.fetch_all_slots_data()
        else:
            logger.warning("Attempted to refresh data but no slot is selected")
            self.connection_panel.set_error_state()

    def fetch_all_slots_data(self):
        """Fetch data from all available slots using parallel processing"""
        if not self.last_ip:
            logger.warning("Empty IP address provided")
            QMessageBox.warning(self, "Input Error", "Please enter a device IP address.")
            return

        # Get all available slots (excluding "All Slots" option)
        slots = []
        for i in range(1, self.connection_panel.slot_combo.count()):
            slot_text = self.connection_panel.slot_combo.itemText(i)
            if slot_text and slot_text.isdigit():
                slots.append(slot_text)
        
        if not slots:
            logger.warning("No slots available to fetch")
            QMessageBox.warning(self, "Error", "No slots available to fetch data from.")
            self.connection_panel.set_error_state()
            return
        
        # Update UI
        self.statusBar().showMessage(f"Fetching data from {len(slots)} slots in parallel...")
        self.connection_panel.set_connecting_state()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(slots))
        self.progress_bar.setValue(0)
        
        # Stop any existing fetcher
        if hasattr(self, 'slot_data_fetcher') and self.slot_data_fetcher:
            self.slot_data_fetcher.stop()
            self.slot_data_fetcher.deleteLater()
            self.slot_data_fetcher = None
        
        # Create new slot data fetcher
        from slot_data_fetcher import SlotDataFetcher
        self.slot_data_fetcher = SlotDataFetcher(self.api_client, slots)
        
        # Connect signals
        self.slot_data_fetcher.progress_updated.connect(self.update_all_slots_progress)
        self.slot_data_fetcher.all_data_ready.connect(self.display_all_slots_data)
        self.slot_data_fetcher.error_occurred.connect(self.handle_all_slots_error)
        self.slot_data_fetcher.finished.connect(self.on_slot_data_fetcher_finished)
        
        # Start fetching
        self.slot_data_fetcher.start()
        logger.info(f"Started parallel fetching for {len(slots)} slots")
    
    def fetch_all_slots_worker(self, slots):
        """Worker function to fetch data from all slots"""
        logger.info(f"Starting to fetch data from {len(slots)} slots")
        self.all_slots_data = {}
        
        for i, slot in enumerate(slots):
            try:
                # Update progress
                self.all_slots_progress = i
                self.statusBar().showMessage(f"Fetching data from slot {slot} ({i+1}/{len(slots)})...")
                self.progress_bar.setValue(i)
                
                # Get data
                data = self.api_client.get_slot_data(slot)
                
                if data and isinstance(data, dict) and data.get('data'):
                    self.all_slots_data[slot] = data
                    logger.info(f"Successfully fetched data for slot {slot}")
                else:
                    logger.warning(f"Failed to get valid data for slot {slot}")
            except Exception as e:
                logger.error(f"Error fetching data for slot {slot}: {str(e)}")
        
        # Complete
        self.all_slots_progress = len(slots)
        self.progress_bar.setValue(len(slots))
        
        # Signal completion on the main thread
        if self.all_slots_data:
            self.all_slots_data_ready.emit(self.all_slots_data)
        else:
            # Handle the case where no data was collected
            self.statusBar().showMessage("Failed to collect data from any slot")
            self.connection_panel.set_error_state()
            self.progress_bar.setVisible(False)

    def update_all_slots_progress(self, current, total):
        """Update the progress bar for all slots operation"""
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"Fetching slot data: {current}/{total} slots completed...")

    def handle_all_slots_error(self, error_msg):
        """Handle errors during all slots fetching"""
        self.statusBar().showMessage("Error fetching slot data")
        self.connection_panel.set_error_state()
        self.progress_bar.setVisible(False)
        
        logger.error(f"All slots fetch error: {error_msg}")
        QMessageBox.critical(self, "Fetch Error", error_msg)

    @pyqtSlot(dict)
    def display_all_slots_data(self, all_slots_data):
        """Display data for all slots"""
        if not all_slots_data:
            logger.warning("No slot data was collected")
            self.statusBar().showMessage("No slot data was collected")
            self.connection_panel.set_error_state()
            self.progress_bar.setVisible(False)
            return
            
        # Store the data
        self.all_slots_data = all_slots_data
        
        # Update UI
        self.connection_panel.set_connected_state()
        self.statusBar().showMessage(f"Connected to all {len(all_slots_data)} slots")
        self.progress_bar.setVisible(False)
        
        # Store last connection
        self.last_slot = "All Slots"
        
        # For now, display data for the first slot
        first_slot = list(all_slots_data.keys())[0]
        first_slot_data = all_slots_data[first_slot]
        
        try:
            device_data = DeviceData(first_slot_data)
            self.info_display.update_display(device_data)
            
            # Log a summary of alarms across all slots
            total_alarms = 0
            critical_alarms = 0
            
            for slot, data in all_slots_data.items():
                try:
                    slot_data = DeviceData(data)
                    if slot_data.alarm_info:
                        slot_alarms = slot_data.alarm_info.get('n_total', 0)
                        slot_critical = slot_data.alarm_info.get('n_critical', 0)
                        total_alarms += int(slot_alarms) if isinstance(slot_alarms, (int, str)) else 0
                        critical_alarms += int(slot_critical) if isinstance(slot_critical, (int, str)) else 0
                except Exception as e:
                    logger.error(f"Error processing data for slot {slot}: {str(e)}")
            
            logger.info(f"Fetched data for {len(all_slots_data)} slots. "
                    f"Total alarms: {total_alarms}, Critical: {critical_alarms}")
            
            # Show a summary message
            self.statusBar().showMessage(f"Connected to all {len(all_slots_data)} slots "
                                    f"(Total alarms: {total_alarms}, Critical: {critical_alarms})")
            
            # Ideally, we would update the UI to show data from all slots
            # For now, we're just showing data from the first slot
            
        except Exception as e:
            logger.error(f"Error processing combined slot data: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Error processing device data: {str(e)}")
        
        # Clean up
        if hasattr(self, 'slot_data_fetcher'):
            self.slot_data_fetcher = None
    
    def cleanup_worker(self, worker_attr):
        """Helper method to safely clean up a worker thread"""
        if hasattr(self, worker_attr) and getattr(self, worker_attr) is not None:
            worker = getattr(self, worker_attr)
            try:
                worker.stop()
                worker.deleteLater()
                setattr(self, worker_attr, None)
                logger.debug(f"Worker {worker_attr} cleaned up")
                return True
            except Exception as e:
                logger.error(f"Error cleaning up {worker_attr}: {str(e)}")
        return False
    
    def on_worker_finished(self):
        """Called when the API worker thread finishes"""
        self.cleanup_worker('worker')
    
    def display_data(self, data):
        """Display the fetched data"""
        self.statusBar().showMessage(f"Connected to slot {self.connection_panel.slot_combo.currentText()}")
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
        
        # Clean up the worker
        self.cleanup_worker('worker')
        
        # Hide progress bar if visible
        self.progress_bar.setVisible(False)
        
        # Refresh button only enabled if we had a successful connection before
        if self.last_ip:
            self.connection_panel.refresh_button.setEnabled(True)
        
        QMessageBox.critical(self, "API Error", error_msg)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up any running threads
        self.cleanup_worker('worker')
        self.cleanup_worker('slot_detection_worker')
        
        # Stop parallel fetcher if running
        if hasattr(self, 'slot_data_fetcher') and self.slot_data_fetcher:
            logger.debug("Stopping slot data fetcher during application close")
            self.slot_data_fetcher.stop()
            self.slot_data_fetcher.deleteLater()
            self.slot_data_fetcher = None
        
        if self.log_viewer:
            self.log_viewer.close()
        
        logger.info("Application closing")
        event.accept()

    def detect_slots(self, ip, username, password):
        """Detect available slots in the device using direct API"""
        logger.info(f"Starting slot detection for {ip}")
        
        # Clean up any existing worker
        self.cleanup_worker('slot_detection_worker')
        
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
            self.statusBar().showMessage(f"Connected - {len(slots)} slots detected. Please select a slot.")
            self.is_connected = True
            
            # Update status in footer
            if hasattr(self, 'footer_label'):
                self.statusBar().removeWidget(self.footer_label)
            self.footer_label = QLabel(f"Detected {len(slots)} slots")
            self.statusBar().addPermanentWidget(self.footer_label)
            
            # Update the connection panel with slots - this will also update the status
            self.connection_panel.update_slots(slots)
            
            # We no longer automatically select a slot - wait for user to select
            
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
        
        # Clean up the worker
        self.cleanup_worker('slot_detection_worker')
        
        # Show error message to the user
        QMessageBox.warning(self, "Slot Detection Error", error_msg)
        
        # Update the UI
        self.connection_panel.set_error_state()
        self.connection_panel.update_slots([])  # Clear slots

    def on_slot_data_fetcher_finished(self):
        """Handle cleanup when the slot data fetcher finishes"""
        logger.debug("Slot data fetcher finished, cleaning up")
        if hasattr(self, 'slot_data_fetcher') and self.slot_data_fetcher:
            # Disconnect all signals
            self.slot_data_fetcher.progress_updated.disconnect()
            self.slot_data_fetcher.all_data_ready.disconnect()
            self.slot_data_fetcher.error_occurred.disconnect()
            self.slot_data_fetcher.finished.disconnect()
            
            # Properly delete the object
            self.slot_data_fetcher.deleteLater()
            self.slot_data_fetcher = None

    def on_slot_selection(self, index):
        """Handle user slot selection"""
        if index >= 0 and self.connection_panel.slot_combo.isEnabled():
            selected_slot = self.connection_panel.slot_combo.currentText()
            if selected_slot == "All Slots":
                logger.info("User selected to fetch data from all slots")
                self.fetch_all_slots_data()
            elif selected_slot and selected_slot != "No slots detected":
                logger.info(f"User selected slot {selected_slot}")
                self.statusBar().showMessage(f"Connecting to slot {selected_slot}...")
                self.fetch_data(self.last_ip, selected_slot, self.last_username, self.last_password)

    def on_slot_detection_finished(self):
        """Clean up after slot detection finishes"""
        self.cleanup_worker('slot_detection_worker')

    def fetch_data(self, ip, slot, username, password):
        """Fetch data from the device API"""
        if not ip:
            logger.warning("Empty IP address provided")
            QMessageBox.warning(self, "Input Error", "Please enter a device IP address.")
            return
        
        if not slot or slot == "All Slots":
            logger.warning("No specific slot selected")
            self.fetch_all_slots_data()
            return
        
        # Clean up any existing worker
        self.cleanup_worker('worker')
        
        # Create or update API client if connection parameters changed
        if (self.api_client is None or
            ip != self.last_ip or
            username != self.last_username or
            password != self.last_password):
            self.api_client = DeviceApiClient(ip, username, password)
            logger.info(f"Created new API client for {ip}")
        
        self.statusBar().showMessage(f"Connecting to slot {slot}...")
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