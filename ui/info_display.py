import json
from PyQt6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QTextEdit

class InfoDisplay(QTabWidget):
    """Widget for displaying device information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components"""
        # Basic information tab
        self.basic_info_widget = QWidget()
        basic_info_layout = QVBoxLayout(self.basic_info_widget)
        
        self.basic_info_text = QTextEdit()
        self.basic_info_text.setReadOnly(True)
        basic_info_layout.addWidget(self.basic_info_text)
        
        self.addTab(self.basic_info_widget, "Basic Info")
        
        # Raw JSON tab
        self.raw_json_widget = QWidget()
        raw_json_layout = QVBoxLayout(self.raw_json_widget)
        
        self.raw_json_text = QTextEdit()
        self.raw_json_text.setReadOnly(True)
        self.raw_json_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        raw_json_layout.addWidget(self.raw_json_text)
        
        self.addTab(self.raw_json_widget, "Raw JSON")
    
    def update_display(self, device_data):
        """Update the display with device data"""
        # Raw JSON display
        self.raw_json_text.setText(json.dumps(device_data.raw_data, indent=4))
        
        # Basic info display
        basic_info = []
        
        # Product information
        if device_data.product_info:
            basic_info.append("=== Product Information ===")
            basic_info.append(f"Name: {device_data.product_info.get('prodname', 'N/A')}")
            basic_info.append(f"Serial: {device_data.product_info.get('serialfull', 'N/A')}")
            basic_info.append(f"Software Version: {device_data.product_info.get('swver', 'N/A')}")
            basic_info.append(f"Build Time: {device_data.product_info.get('swbuildtime', 'N/A')}")
            basic_info.append("")
        
        # Time information
        if device_data.time_info:
            basic_info.append("=== Time Information ===")
            basic_info.append(f"Current Time: {device_data.time_info.get('localtimetxt', 'N/A')}")
            basic_info.append(f"Uptime: {device_data.time_info.get('uptimetxt', 'N/A')}")
            basic_info.append("")
        
        # Memory usage
        if device_data.memory_info:
            basic_info.append("=== Memory Usage ===")
            basic_info.append(f"Threshold: {device_data.memory_info.get('threshold', 'N/A')}%")
            
            # Pool collection
            if 'pool_coll' in device_data.memory_info:
                for pool_id, pool in device_data.memory_info['pool_coll'].items():
                    try:
                        # Convert string values to integers before calculation
                        used = int(pool.get('used', 0)) if isinstance(pool.get('used'), (int, str)) else 0
                        size = int(pool.get('size', 1)) if isinstance(pool.get('size'), (int, str)) else 1
                        
                        # Prevent division by zero
                        if size > 0:
                            usage_percent = (used / size) * 100
                            basic_info.append(f"Pool {pool_id}: {usage_percent:.1f}% used ({used}/{size} bytes)")
                        else:
                            basic_info.append(f"Pool {pool_id}: 0.0% used ({used}/0 bytes)")
                    except (ValueError, TypeError) as e:
                        # Handle case where values can't be converted to int
                        basic_info.append(f"Pool {pool_id}: N/A% used ({pool.get('used', 'N/A')}/{pool.get('size', 'N/A')} bytes)")
            basic_info.append("")
        
        # Alarm information
        if device_data.alarm_info:
            basic_info.append("=== Alarm Information ===")
            basic_info.append(f"Total Alarms: {device_data.alarm_info.get('n_total', 'N/A')}")
            basic_info.append(f"Critical Alarms: {device_data.alarm_info.get('n_critical', 'N/A')}")
            basic_info.append(f"Major Alarms: {device_data.alarm_info.get('n_major', 'N/A')}")
            basic_info.append(f"Minor Alarms: {device_data.alarm_info.get('n_minor', 'N/A')}")
            basic_info.append(f"Warning Alarms: {device_data.alarm_info.get('n_warning', 'N/A')}")
        
        self.basic_info_text.setText("\n".join(basic_info))