from utils.logger import logger

class DeviceData:
    """Class representing device data"""
    
    def __init__(self, raw_data):
        self.raw_data = raw_data
        logger.debug("Processing device data")
        
        # The data may now be in a different structure
        self.product_info = self._extract_product_info()
        self.time_info = self._extract_time_info()
        self.memory_info = self._extract_memory_info()
        self.alarm_info = self._extract_alarm_info()
        
        logger.debug("Device data processing complete")
    
    def _extract_product_info(self):
        """Extract product information from raw data"""
        try:
            # First try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'product_info' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['product_info']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data:
                dev_info = self.raw_data['device_info']
                if 'product_info' in dev_info:
                    return dev_info['product_info']
                
            # Try other possible section names
            for section_name in ['dev', 'device']:
                if section_name in self.raw_data and 'product_info' in self.raw_data[section_name]:
                    return self.raw_data[section_name]['product_info']
            
            return {}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract product info: {e}")
            return {}
    
    def _extract_time_info(self):
        """Extract time information from raw data"""
        try:
            # First try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'time' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['time']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data and 'time' in self.raw_data['device_info']:
                return self.raw_data['device_info']['time']
                
            # Try other possible section names
            for section_name in ['dev', 'device', 'time']:
                if section_name in self.raw_data:
                    if 'time' in self.raw_data[section_name]:
                        return self.raw_data[section_name]['time']
                    elif 'timetxt' in self.raw_data[section_name]:  # Directly contains time fields
                        return self.raw_data[section_name]
            
            return {}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract time info: {e}")
            return {}
    
    def _extract_memory_info(self):
        """Extract memory usage information from raw data"""
        try:
            # First try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'mem_usage' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['mem_usage']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data and 'mem_usage' in self.raw_data['device_info']:
                return self.raw_data['device_info']['mem_usage']
                
            # Try other possible section names
            for section_name in ['dev', 'device', 'memory', 'mem_usage']:
                if section_name in self.raw_data:
                    if 'mem_usage' in self.raw_data[section_name]:
                        return self.raw_data[section_name]['mem_usage']
                    elif 'pool_coll' in self.raw_data[section_name]:  # Directly contains memory fields
                        return self.raw_data[section_name]
            
            return {}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract memory info: {e}")
            return {}
    
    def _extract_alarm_info(self):
        """Extract alarm information from raw data"""
        try:
            # First try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'alarms' in self.raw_data['data']['dev'] and 'status' in self.raw_data['data']['dev']['alarms']:
                return self.raw_data['data']['dev']['alarms']['status']['severities']
            
            # Try the new sectioned structure
            if 'alarms' in self.raw_data:
                alarms_section = self.raw_data['alarms']
                
                # Check various possible paths to alarm severities
                if 'status' in alarms_section and 'severities' in alarms_section['status']:
                    return alarms_section['status']['severities']
                elif 'severities' in alarms_section:
                    return alarms_section['severities']
                elif 'group_status' in alarms_section and 'glob_severities' in alarms_section['group_status']:
                    return alarms_section['group_status']['glob_severities']
            
            # Try device_info section
            if 'device_info' in self.raw_data and 'alarms' in self.raw_data['device_info']:
                dev_alarms = self.raw_data['device_info']['alarms']
                if 'status' in dev_alarms and 'severities' in dev_alarms['status']:
                    return dev_alarms['status']['severities']
            
            return {}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract alarm info: {e}")
            return {}