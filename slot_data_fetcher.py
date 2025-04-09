import concurrent.futures
import time
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread, QTimer

from utils.logger import logger

class SlotDataFetcher(QObject):
    """Class to manage concurrent fetching of data from multiple slots"""
    
    # Signals
    progress_updated = pyqtSignal(int, int)  # current, total
    all_data_ready = pyqtSignal(dict)  # slot_data dictionary
    error_occurred = pyqtSignal(str)  # error message
    finished = pyqtSignal()  # Signal emitted when fetching is complete
    
    def __init__(self, api_client, slots, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.slots = slots
        self.all_slots_data = {}
        self.is_running = False
        self.thread = None
        
        # Performance tuning parameters
        self.max_workers = min(8, len(slots))  # Limit number of parallel requests
        self.update_interval = 0.2  # Batch UI updates (seconds)
        self.last_update_time = 0
        self.completed_slots = 0
    
    def start(self):
        """Start fetching data from all slots in a separate thread"""
        if self.is_running:
            logger.warning("Already fetching slot data")
            return
            
        self.is_running = True
        self.all_slots_data = {}
        self.completed_slots = 0
        self.last_update_time = time.time()
        
        # Create and start the worker thread
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.fetch_all_data)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
    
    def stop(self):
        """Stop the fetching process"""
        if not self.is_running:
            return
            
        logger.debug("Stopping SlotDataFetcher")
        self.is_running = False
        
        if self.thread:
            if self.thread.isRunning():
                logger.debug("Requesting thread termination")
                self.thread.quit()
                if not self.thread.wait(2000):  # Wait up to 2 seconds
                    logger.warning("Thread did not terminate gracefully, forcing termination")
                    self.thread.terminate()
                    self.thread.wait(1000)  # Wait for forced termination
            
            # The thread will call deleteLater on itself through the connection to finished
            self.thread = None
            
        logger.debug("SlotDataFetcher stopped")
    
    def fetch_all_data(self):
        """Fetch data from all slots in parallel using a thread pool"""
        logger.info(f"Starting parallel fetch for {len(self.slots)} slots with {self.max_workers} workers")
        start_time = time.time()
        
        try:
            # Using ThreadPoolExecutor for parallel fetching
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all fetch jobs
                future_to_slot = {
                    executor.submit(self.fetch_slot_data, slot): slot 
                    for slot in self.slots
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_slot):
                    if not self.is_running:
                        logger.info("Fetch operation was stopped")
                        break
                        
                    slot = future_to_slot[future]
                    try:
                        data = future.result()
                        if data:
                            self.all_slots_data[slot] = data
                    except Exception as e:
                        logger.error(f"Error fetching data for slot {slot}: {str(e)}")
                    
                    # Update progress (but limit update frequency)
                    self.completed_slots += 1
                    current_time = time.time()
                    if (current_time - self.last_update_time >= self.update_interval or 
                        self.completed_slots == len(self.slots)):
                        self.progress_updated.emit(self.completed_slots, len(self.slots))
                        self.last_update_time = current_time
            
            # Emit final data
            if self.is_running:
                logger.info(f"Completed fetching data from {len(self.all_slots_data)} slots in {time.time() - start_time:.2f} seconds")
                self.all_data_ready.emit(self.all_slots_data)
            
        except Exception as e:
            error_msg = f"Error in parallel fetch operation: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
        
        finally:
            self.is_running = False
            self.finished.emit()
            # Make sure we exit the thread's event loop
            if QThread.currentThread() is not None:
                QThread.currentThread().quit()
    
    def fetch_slot_data(self, slot):
        """Fetch data for a single slot (optimized version)"""
        try:
            logger.debug(f"Fetching data for slot {slot}")
            
            # For the all slots view, we use a focused approach to only fetch essential data
            # This significantly reduces the data and time needed per slot
            data = self.api_client.get_focused_slot_data(slot)
            
            if data and isinstance(data, dict) and data.get('data'):
                logger.debug(f"Successfully fetched focused data for slot {slot}")
                return data
            else:
                logger.warning(f"Invalid or empty data returned for slot {slot}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data for slot {slot}: {str(e)}")
            return None