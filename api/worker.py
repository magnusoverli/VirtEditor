import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal
from utils.logger import logger

class ApiWorker(QThread):
    """Worker thread to fetch data from the API"""
    dataReady = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, client, slot):
        super().__init__()
        self.client = client
        self.slot = slot
        
    def run(self):
        logger.debug(f"API worker started for slot {self.slot}")
        try:
            logger.info(f"Fetching data from slot {self.slot}")
            data = self.client.get_slot_data(self.slot)
            
            # Check if data is empty due to authentication failure
            if not data:
                logger.error("Empty data returned, likely due to authentication failure")
                self.error.emit("Authentication failed. Please check username and password.")
                return
                
            # Check for data structure to verify we have actual content
            if not isinstance(data, dict) or not data.get('data'):
                logger.error("Invalid or empty data structure returned")
                self.error.emit("Failed to retrieve valid data from the device.")
                return
                
            logger.debug(f"Data received from slot {self.slot}")
            self.dataReady.emit(data)
            
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error. Please check the device IP and network connection."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except requests.exceptions.Timeout:
            error_msg = "Connection timed out. The device might be busy or unreachable."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check username and password."
                logger.error(error_msg)
                self.error.emit(error_msg)
            else:
                error_msg = f"HTTP Error: {str(e)}"
                logger.error(error_msg)
                self.error.emit(error_msg)
        except json.JSONDecodeError:
            error_msg = "Invalid JSON response from the device."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"Error fetching data: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)

class SlotDetectionWorker(QThread):
    """Worker thread to detect available slots"""
    slotsDetected = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, client, max_slots=10, use_direct_api=True):
        super().__init__()
        self.client = client
        self.max_slots = max_slots
        self.use_direct_api = use_direct_api
        
    def run(self):
        logger.debug(f"Slot detection worker started (max slots: {self.max_slots}, use direct API: {self.use_direct_api})")
        try:
            if self.use_direct_api:
                # Try the direct API first
                slots = self.client.detect_slots_direct()
            else:
                # Use the original method
                slots = self.client.detect_slots(self.max_slots)
                
            logger.debug(f"Slot detection complete, found: {slots}")
            self.slotsDetected.emit(slots)
        except Exception as e:
            error_msg = f"Error detecting slots: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)