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
            # Try the actual nested structure we can see in the JSON
            if ('data' in self.raw_data and 'dev' in self.raw_data['data'] and 
                'data' in self.raw_data['data']['dev'] and 'dev' in self.raw_data['data']['dev']['data'] and
                'product_info' in self.raw_data['data']['dev']['data']['dev']):
                return self.raw_data['data']['dev']['data']['dev']['product_info']
            
            # Try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'product_info' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['product_info']
            
            # Try other possible paths
            if 'dev' in self.raw_data and 'data' in self.raw_data['dev'] and 'dev' in self.raw_data['dev']['data']:
                if 'product_info' in self.raw_data['dev']['data']['dev']:
                    return self.raw_data['dev']['data']['dev']['product_info']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data:
                dev_info = self.raw_data['device_info']
                if 'product_info' in dev_info:
                    return dev_info['product_info']
            
            # Return default structure instead of empty dict
            logger.warning("Could not find product info in expected structures")
            return {'prodname': 'Unknown', 'serialfull': 'Unknown', 'swver': 'Unknown', 'swbuildtime': 'Unknown'}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract product info: {e}")
            return {'prodname': 'Unknown', 'serialfull': 'Unknown', 'swver': 'Unknown', 'swbuildtime': 'Unknown'}

    def _extract_time_info(self):
        """Extract time information from raw data"""
        try:
            # Try the actual nested structure we can see in the JSON
            if ('data' in self.raw_data and 'dev' in self.raw_data['data'] and 
                'data' in self.raw_data['data']['dev'] and 'dev' in self.raw_data['data']['dev']['data'] and
                'time' in self.raw_data['data']['dev']['data']['dev']):
                return self.raw_data['data']['dev']['data']['dev']['time']
                
            # Try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'time' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['time']
            
            # Try other possible paths
            if 'dev' in self.raw_data and 'data' in self.raw_data['dev'] and 'dev' in self.raw_data['dev']['data']:
                if 'time' in self.raw_data['dev']['data']['dev']:
                    return self.raw_data['dev']['data']['dev']['time']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data and 'time' in self.raw_data['device_info']:
                return self.raw_data['device_info']['time']
            
            # Return default structure instead of empty dict
            logger.warning("Could not find time info in expected structures")
            return {'localtimetxt': 'Unknown', 'uptimetxt': 'Unknown'}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract time info: {e}")
            return {'localtimetxt': 'Unknown', 'uptimetxt': 'Unknown'}

    def _extract_memory_info(self):
        """Extract memory usage information from raw data"""
        try:
            # Try the actual nested structure we can see in the JSON
            if ('data' in self.raw_data and 'dev' in self.raw_data['data'] and 
                'data' in self.raw_data['data']['dev'] and 'dev' in self.raw_data['data']['dev']['data'] and
                'mem_usage' in self.raw_data['data']['dev']['data']['dev']):
                return self.raw_data['data']['dev']['data']['dev']['mem_usage']
            
            # Try the original structure
            if 'data' in self.raw_data and 'dev' in self.raw_data['data'] and 'mem_usage' in self.raw_data['data']['dev']:
                return self.raw_data['data']['dev']['mem_usage']
            
            # Try other possible paths
            if 'dev' in self.raw_data and 'data' in self.raw_data['dev'] and 'dev' in self.raw_data['dev']['data']:
                if 'mem_usage' in self.raw_data['dev']['data']['dev']:
                    return self.raw_data['dev']['data']['dev']['mem_usage']
            
            # Try the new sectioned structure
            if 'device_info' in self.raw_data and 'mem_usage' in self.raw_data['device_info']:
                return self.raw_data['device_info']['mem_usage']
            
            # Return default structure instead of empty dict
            logger.warning("Could not find memory info in expected structures")
            return {'threshold': '0', 'pool_coll': {}}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract memory info: {e}")
            return {'threshold': '0', 'pool_coll': {}}

    def _extract_alarm_info(self):
        """Extract alarm information from raw data"""
        try:
            # Try the actual nested structure we can see in the JSON
            if ('data' in self.raw_data and 'dev' in self.raw_data['data'] and 
                'data' in self.raw_data['data']['dev'] and 'dev' in self.raw_data['data']['dev']['data'] and
                'alarms' in self.raw_data['data']['dev']['data']['dev'] and 
                'status' in self.raw_data['data']['dev']['data']['dev']['alarms']):
                
                # From the JSON tree, it seems the status might directly contain the alarm info
                status = self.raw_data['data']['dev']['data']['dev']['alarms']['status']
                
                # If there's a 'severities' key, use it
                if 'severities' in status:
                    return status['severities']
                
                # If not, try to build a default structure from available status data
                # Just ensure we have the keys the UI expects
                alarm_info = {}
                alarm_info['n_total'] = status.get('active_count', 0) if 'active_count' in status else 0
                alarm_info['n_critical'] = status.get('critical_count', 0) if 'critical_count' in status else 0
                alarm_info['n_major'] = status.get('major_count', 0) if 'major_count' in status else 0
                alarm_info['n_minor'] = status.get('minor_count', 0) if 'minor_count' in status else 0
                alarm_info['n_warning'] = status.get('warning_count', 0) if 'warning_count' in status else 0
                
                return alarm_info
                
            # Try the original structure
            if ('data' in self.raw_data and 'dev' in self.raw_data['data'] and 
                'alarms' in self.raw_data['data']['dev'] and 'status' in self.raw_data['data']['dev']['alarms']):
                
                status = self.raw_data['data']['dev']['alarms']['status']
                if 'severities' in status:
                    return status['severities']
            
            # Try the sectioned structure
            if 'alarms' in self.raw_data:
                alarms_section = self.raw_data['alarms']
                if 'status' in alarms_section:
                    if 'severities' in alarms_section['status']:
                        return alarms_section['status']['severities']
                    # If no severities, try the status directly
                    return alarms_section['status']
            
            # Return default structure with expected fields
            logger.warning("Could not find alarm info in expected structures")
            return {'n_total': '0', 'n_critical': '0', 'n_major': '0', 'n_minor': '0', 'n_warning': '0'}
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract alarm info: {e}")
            return {'n_total': '0', 'n_critical': '0', 'n_major': '0', 'n_minor': '0', 'n_warning': '0'}