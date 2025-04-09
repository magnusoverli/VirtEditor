import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from utils.logger import logger

from api.base_worker import BaseApiWorker

class ApiWorker(BaseApiWorker):
    """Worker thread to fetch data from the API"""
    dataReady = pyqtSignal(dict)
    
    def __init__(self, client, slot):
        super().__init__()
        self.client = client
        self.slot = slot
        
    def run(self):
        logger.debug(f"API worker started for slot {self.slot}")
        try:
            if not self.running:
                return
                
            logger.info(f"Fetching data from slot {self.slot}")
            data = self.client.get_slot_data(self.slot)
            
            if not self.running:
                return
                
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
            if not self.running:
                return
            error_msg = "Connection error. Please check the device IP and network connection."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except requests.exceptions.Timeout:
            if not self.running:
                return
            error_msg = "Connection timed out. The device might be busy or unreachable."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except requests.exceptions.HTTPError as e:
            if not self.running:
                return
            if e.response.status_code == 401:
                error_msg = "Authentication failed. Please check username and password."
                logger.error(error_msg)
                self.error.emit(error_msg)
            else:
                error_msg = f"HTTP Error: {str(e)}"
                logger.error(error_msg)
                self.error.emit(error_msg)
        except json.JSONDecodeError:
            if not self.running:
                return
            error_msg = "Invalid JSON response from the device."
            logger.error(error_msg)
            self.error.emit(error_msg)
        except Exception as e:
            if not self.running:
                return
            error_msg = f"Error fetching data: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)

class SlotDetectionWorker(BaseApiWorker):
    """Worker thread to detect available slots"""
    slotsDetected = pyqtSignal(list)
    
    def __init__(self, client, max_slots=10):
        super().__init__()
        self.client = client
        self.max_slots = max_slots
        
    def run(self):
        logger.debug(f"Slot detection worker started (max slots: {self.max_slots})")
        try:
            if not self.running:
                return
                
            slots = self.client.detect_slots(self.max_slots)
            
            if not self.running:
                return
                
            logger.debug(f"Slot detection complete, found: {slots}")
            self.slotsDetected.emit(slots)
        except Exception as e:
            if not self.running:
                return
            error_msg = f"Error detecting slots: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)