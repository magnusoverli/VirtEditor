import requests
import json
import re
from bs4 import BeautifulSoup
from utils.logger import logger

class DeviceApiClient:
    """Client for interacting with the device API"""
    
    def __init__(self, base_ip, username, password):
        self.base_ip = base_ip
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False
        logger.debug(f"Created API client for {base_ip}")
    
    def authenticate(self):
        """Authenticate with the device using form-based login"""
        if self.authenticated:
            return True
            
        try:
            # Step 1: Get the login page to establish a session and get any CSRF tokens
            login_url = f"http://{self.base_ip}/slot/1/api/data.html"  # Use a known URL that requires auth
            logger.debug(f"Fetching login page: {login_url}")
            
            response = self.session.get(login_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to access login page: status code {response.status_code}")
                return False
                
            # Check if we get redirected to a login page
            if "login" in response.url.lower() or "login" in response.text.lower():
                logger.debug("Found login page")
                
                # Parse the HTML to find the login form
                soup = BeautifulSoup(response.text, 'html.parser')
                login_form = soup.find('form')
                
                if not login_form:
                    logger.error("Could not find login form in the login page")
                    return False
                
                # Get the form action (submission URL)
                form_action = login_form.get('action', '/api/login')  # Default if not specified
                if not form_action.startswith('http'):
                    # Convert relative URL to absolute
                    form_action = f"http://{self.base_ip}{form_action if form_action.startswith('/') else '/' + form_action}"
                
                logger.debug(f"Login form action: {form_action}")
                
                # Prepare form data
                form_data = {
                    'us': self.username,  # Common field name for username
                    'pw': self.password   # Common field name for password
                }
                
                # Check the actual field names from the form
                username_field = login_form.find('input', {'name': True, 'type': 'text'})
                password_field = login_form.find('input', {'name': True, 'type': 'password'})
                
                if username_field and username_field.get('name'):
                    form_data = {username_field.get('name'): self.username}
                    
                if password_field and password_field.get('name'):
                    form_data[password_field.get('name')] = self.password
                
                # Look for any hidden fields (like CSRF tokens)
                for hidden_field in login_form.find_all('input', {'type': 'hidden', 'name': True}):
                    field_name = hidden_field.get('name')
                    field_value = hidden_field.get('value', '')
                    form_data[field_name] = field_value
                
                logger.debug(f"Submitting login form with fields: {list(form_data.keys())}")
                
                # Submit the login form
                login_response = self.session.post(form_action, data=form_data, timeout=10, 
                                                 allow_redirects=True)
                
                # Check if login was successful
                if login_response.status_code == 200:
                    # Try to verify we're logged in by looking for typical failed login messages
                    failed_patterns = ["login failed", "invalid username", "invalid password", 
                                      "authentication failed", "incorrect credentials"]
                    
                    login_failed = any(pattern in login_response.text.lower() for pattern in failed_patterns)
                    
                    if login_failed:
                        logger.error("Login failed: Invalid credentials")
                        return False
                    
                    # If we don't see failure messages, assume success
                    logger.info("Successfully authenticated with the device")
                    self.authenticated = True
                    return True
                else:
                    logger.error(f"Login form submission failed: status code {login_response.status_code}")
                    return False
            else:
                # If we didn't get redirected to a login page, we might already be authenticated
                logger.info("No login page detected, might already be authenticated")
                self.authenticated = True
                return True
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def detect_slots(self, max_slots=10):
        """Detect available slots in the device by probing each potential slot"""
        logger.info(f"Detecting available slots (up to {max_slots})")
        
        # Ensure we're authenticated
        if not self.authenticate():
            logger.error("Failed to authenticate, cannot detect slots")
            return []
        
        available_slots = []
        
        # Check each possible slot
        for slot in range(1, max_slots + 1):
            try:
                # Try a lightweight request that's likely to work if the slot exists
                # Using dev.json as it's a common endpoint that should exist for all slots
                url = f"http://{self.base_ip}/slot/{slot}/api/data/dev.json"
                logger.debug(f"Probing slot {slot} at {url}")
                
                response = self.session.get(url, timeout=5)  # Shorter timeout for probing
                
                # If we get a successful response or a specific error that indicates the slot exists
                if response.status_code == 200:
                    logger.info(f"Slot {slot} is available")
                    available_slots.append(slot)
                elif response.status_code == 404:
                    logger.debug(f"Slot {slot} not found (404)")
                else:
                    logger.debug(f"Slot {slot} returned status code {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error probing slot {slot}: {str(e)}")
        
        if not available_slots:
            logger.warning("No slots detected, defaulting to slot 1")
            return [1]  # Default to slot 1 if none detected
        
        logger.info(f"Detected {len(available_slots)} slots: {available_slots}")
        return available_slots

    def detect_slots_direct(self):
        """Detect available slots in the device using direct API endpoint
        
        This method uses the shelf/slots/detected_coll API endpoint to get all detected
        slots in a single request, which is more efficient than probing each slot individually.
        
        Returns:
            list: A sorted list of detected slot numbers
        """
        logger.info("Detecting available slots using direct API endpoint")
        
        # Ensure we're authenticated
        if not self.authenticate():
            logger.error("Failed to authenticate, cannot detect slots")
            return []
        
        try:
            # Use the direct API endpoint for slot detection
            url = f"http://{self.base_ip}/api/data/shelf/slots/detected_coll"
            logger.debug(f"Fetching slots from direct API: {url}")
            
            response = self.session.get(url, timeout=10)
            
            # Check if we got redirected to login page
            if "login" in response.url.lower() or (
                response.status_code == 200 and "login" in response.text.lower()[:1000]):
                logger.warning("Session expired, attempting to re-authenticate")
                # Try to authenticate again
                self.authenticated = False
                if not self.authenticate():
                    logger.error("Re-authentication failed")
                    return []
                
                # Retry the request
                response = self.session.get(url, timeout=10)
                
            if response.status_code == 200:
                # Parse the JSON response
                try:
                    data = response.json()
                    # Extract slot numbers from the response
                    slots = []
                    # The structure is expected to be: data -> shelf -> slots -> detected_coll -> {slot_numbers}
                    if (data and 'data' in data and 'shelf' in data['data'] and 
                        'slots' in data['data']['shelf'] and 'detected_coll' in data['data']['shelf']['slots']):
                        detected_slots = data['data']['shelf']['slots']['detected_coll']
                        # The keys in detected_coll should be slot numbers (as strings)
                        slots = [int(slot_num) for slot_num in detected_slots.keys()]
                        logger.info(f"Successfully detected {len(slots)} slots via direct API: {slots}")
                        return sorted(slots)  # Return slots in numerical order
                    else:
                        logger.warning("Unexpected response structure from direct API")
                        logger.debug(f"Response: {data}")
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from direct API")
                    # Try to extract JSON content if not valid JSON
                    json_content = self._extract_json_from_content(response.text)
                    if json_content:
                        logger.debug("Extracted JSON content, trying to process again")
                        # Process the extracted JSON
                        try:
                            if (json_content and 'data' in json_content and 'shelf' in json_content['data'] and 
                                'slots' in json_content['data']['shelf'] and 'detected_coll' in json_content['data']['shelf']['slots']):
                                detected_slots = json_content['data']['shelf']['slots']['detected_coll']
                                slots = [int(slot_num) for slot_num in detected_slots.keys()]
                                logger.info(f"Successfully detected {len(slots)} slots via direct API (from extracted JSON): {slots}")
                                return sorted(slots)
                        except Exception as e:
                            logger.error(f"Error processing extracted JSON: {str(e)}")
            else:
                logger.warning(f"Failed to fetch slots via direct API: status code {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching slots via direct API: {str(e)}")
        
        # Fallback to the original method if direct API fails
        logger.info("Falling back to slot-by-slot detection")
        return self.detect_slots()

    def get_slot_data(self, slot_number):
        """Get comprehensive data from a specific slot/card"""
        # Ensure we're authenticated
        if not self.authenticate():
            logger.error("Failed to authenticate, cannot fetch data")
            # Return None to explicitly indicate authentication failure
            return None
        
        logger.debug(f"Fetching data for slot {slot_number}")
        
        # Define the sections we want to fetch
        sections = {
            "dev": f"http://{self.base_ip}/slot/{slot_number}/api/data/dev.json",
            "store": f"http://{self.base_ip}/slot/{slot_number}/api/data/store.json",
            "alarms": f"http://{self.base_ip}/slot/{slot_number}/api/data/alarms.json"
        }
        
        # Optional sections to try if available
        optional_sections = {
            "shelf": f"http://{self.base_ip}/slot/{slot_number}/api/data/shelf.json",
            "elements": f"http://{self.base_ip}/slot/{slot_number}/api/data/elements.json",
            "network": f"http://{self.base_ip}/slot/{slot_number}/api/data/network.json"
        }
        
        # Combine required and optional sections
        all_sections = {**sections, **optional_sections}
        
        # Fetch each section
        combined_data = {"data": {}}
        for section_name, section_url in all_sections.items():
            logger.debug(f"Fetching section '{section_name}' from {section_url}")
            
            try:
                response = self.session.get(section_url, timeout=10)
                
                # Check if we got redirected to login page
                if "login" in response.url.lower() or (
                    response.status_code == 200 and "login" in response.text.lower()[:1000]):
                    logger.warning("Session expired, attempting to re-authenticate")
                    # Try to authenticate again
                    self.authenticated = False
                    if not self.authenticate():
                        logger.error("Re-authentication failed")
                        continue
                    
                    # Retry the request
                    response = self.session.get(section_url, timeout=10)
                
                if response.status_code == 200:
                    # Try to parse as JSON
                    try:
                        section_data = response.json()
                        # Add to combined data
                        combined_data["data"][section_name] = section_data
                        logger.debug(f"Successfully fetched section '{section_name}'")
                    except json.JSONDecodeError:
                        # If not valid JSON, try to extract JSON from content
                        logger.debug(f"Response is not valid JSON, trying to extract JSON content")
                        json_content = self._extract_json_from_content(response.text)
                        if json_content:
                            combined_data["data"][section_name] = json_content
                            logger.debug(f"Extracted JSON for section '{section_name}'")
                        else:
                            logger.warning(f"Could not extract JSON for section '{section_name}'")
                else:
                    # Log but don't fail for optional sections
                    if section_name in optional_sections:
                        logger.debug(f"Optional section '{section_name}' not available (status code {response.status_code})")
                    else:
                        logger.warning(f"Failed to fetch section '{section_name}': status code {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                # Log but don't fail for optional sections
                if section_name in optional_sections:
                    logger.debug(f"Optional section '{section_name}' not available: {str(e)}")
                else:
                    logger.warning(f"Error fetching section '{section_name}': {str(e)}")
        
        # Verify we have at least some data
        if not combined_data["data"]:
            logger.error("No data sections were successfully fetched")
            # Try fallback to direct data.json
            return self._fallback_get_data(slot_number)
        
        # Log success
        logger.info(f"Successfully fetched {len(combined_data['data'])} data sections")
        return combined_data
    
    def _extract_json_from_content(self, content):
        """Extract JSON data from string content"""
        try:
            # If content looks like a pretty-printed JSON, strip the "pretty print" header
            if content.strip().startswith("Pretty-print") and "{" in content:
                content = content[content.find("{"):]
            
            # If content is already JSON, just parse it
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
            
            # Look for JSON-like content (between { and })
            logger.debug("Looking for JSON-like content in response")
            if '{' in content and '}' in content:
                # Simple approach: find the first { and last }
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    json_text = content[start:end]
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        logger.warning("Could not parse extracted content as JSON")
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from content: {str(e)}")
            return None
    
    def _fallback_get_data(self, slot_number):
        """Fallback method using the original data.json approach"""
        try:
            url = f"http://{self.base_ip}/slot/{slot_number}/api/data.json"
            logger.debug(f"Trying fallback direct JSON URL: {url}")
            
            response = self.session.get(url, timeout=10)
            
            # Check if we got redirected to login page
            if "login" in response.url.lower() or (
                response.status_code == 200 and "login" in response.text.lower()[:1000]):
                logger.warning("Session expired in fallback, attempting to re-authenticate")
                # Try to authenticate again
                self.authenticated = False
                if not self.authenticate():
                    logger.error("Re-authentication failed in fallback")
                    return {}
                
                # Retry the request
                response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract JSON
                    json_content = self._extract_json_from_content(response.text)
                    if json_content:
                        return json_content
                    else:
                        logger.error("Could not extract JSON from fallback response")
                        return {}
            else:
                logger.error(f"Fallback request failed: status code {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Fallback method failed: {str(e)}")
            return {}