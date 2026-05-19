#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Tulip
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: tulip_edge_api
short_description: Manage Tulip Edge devices via HTTP API
version_added: "1.0.0"
description:
    - This module provides a common interface for interacting with Tulip Edge device HTTP APIs
    - Supports authentication, token management, and various device operations
options:
    host:
        description: The hostname or IP address of the Tulip Edge device
        required: true
        type: str
    port:
        description: The port number for the HTTP API
        required: false
        type: int
        default: 80
    use_https:
        description: Whether to use HTTPS instead of HTTP
        required: false
        type: bool
        default: false
    action:
        description: The action to perform
        required: true
        type: str
        choices:
            - register
            - login
            - toggle_nodered
            - backup_nodered
            - restore_nodered
            - upgrade_nodered
            - rollback_nodered
            - change_password
            - factory_reset
            - enable_mqtt_broker
            - disable_mqtt_broker
            - backup_mqtt_broker
            - restore_mqtt_broker
            - toggle_mqtt_bridge
            - restore_mqtt_bridge
            - backup_mqtt_bridge
            - backup_lightkit
            - restore_lightkit
            - configure_network
            - restore_root_certs
            - backup_root_certs
            - toggle_http_proxy
            - configure_http_proxy
            - configure_ntp
            - toggle_https
            - configure_https
            - backup_drivers
            - restore_drivers
            - backup_network_state
            - restore_network_config
            - confirm_network_config
    username:
        description: Username for authentication
        required: false
        type: str
        default: tulip
    password:
        description: Password for authentication
        required: false
        type: str
    token:
        description: Authentication token (if already logged in)
        required: false
        type: str
    parameters:
        description: Additional parameters for the specific action
        required: false
        type: dict
        default: {}
    timeout:
        description: Request timeout in seconds
        required: false
        type: int
        default: 30
author:
    - Tulip Team
'''

EXAMPLES = r'''
- name: Register device with password
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: register
    password: "{{ device_password }}"

- name: Login to device
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: login
    password: "{{ device_password }}"
  register: login_result

- name: Toggle Node-RED service
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: toggle_nodered
    token: "{{ auth_token }}"
    parameters:
      enabled: true

- name: Configure network settings
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: configure_network
    token: "{{ auth_token }}"
    parameters:
      interface: eth0
      ip: 192.168.1.100
      netmask: 255.255.255.0
      gateway: 192.168.1.1
'''

RETURN = r'''
result:
    description: The result of the API call
    type: dict
    returned: always
    sample: {"status": "success", "message": "Operation completed"}
token:
    description: Authentication token (returned by login action)
    type: str
    returned: when action is login and successful
changed:
    description: Whether the operation changed the device state
    type: bool
    returned: always
failed:
    description: Whether the operation failed
    type: bool
    returned: always
'''

import json
import traceback
import hashlib
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url
from ansible.module_utils._text import to_text


class TulipEdgeAPI:
    def __init__(self, module):
        self.module = module
        self.host = module.params['host']
        self.port = module.params['port']
        self.use_https = module.params['use_https']
        self.timeout = module.params['timeout']
        
        protocol = 'https' if self.use_https else 'http'
        self.base_url = f"{protocol}://{self.host}:{self.port}/api/v0"
        
    def _make_request(self, endpoint, method='GET', data=None, headers=None, port=80):
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"
        
        # Debug info
        debug_info = {
            'url': url,
            'method': method,
            'headers': headers,
            'data_sent': data if data else None
        }
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        if data and isinstance(data, dict):
            data = json.dumps(data)
        
        resp, info = fetch_url(
            self.module,
            url,
            data=data,
            headers=headers,
            method=method,
            timeout=self.timeout
        )
        
        debug_info['status_code'] = info.get('status', 'unknown')
        debug_info['response_info'] = info
        
        if info['status'] >= 400:
            debug_info['error'] = f"API request failed: {info['status']} {info.get('msg', '')}"
            self.module.fail_json(
                msg=f"API request failed: {info['status']} {info.get('msg', '')}",
                url=url,
                status_code=info['status'],
                debug_info=debug_info
            )
        
        try:
            response_data = json.loads(resp.read()) if resp else {}
        except (ValueError, TypeError):
            response_data = {}
        
        debug_info['response_data'] = response_data
        
        return response_data, info, debug_info
    
    def _hash_password(self, password, serial_number=None):
        """Hash password with SHA256 like the frontend does"""
        if serial_number:
            # Hash with serial number prefix like the frontend: sha256(serialNumber + password)
            combined = serial_number + password
        else:
            # Fallback to just password if no serial number provided
            combined = password
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def register(self, password):
        """Register device with password"""
        # For register, we might not have serial number yet, use device name as fallback
        device_name = self.module.params.get('device_name', '')
        hashed_password = self._hash_password(password, device_name)
        data = {'new_pass': hashed_password}
        result, info, debug_info = self._make_request('/password', method='PUT', data=data)
        return {'result': result, 'changed': True, 'debug_info': debug_info}
    
    def login(self, username, password):
        """Login and get authentication token"""
        # Use device name (inventory hostname) as serial number for hashing
        device_name = self.module.params.get('device_name', '')
        hashed_password = self._hash_password(password, device_name)
        data = {'username': username, 'password': hashed_password}
        result, info, debug_info = self._make_request('/auth/loginToken', method='POST', data=data)
        
        # Extract token from nested structure: {"data": {"token": "..."}}
        if 'data' in result and 'token' in result['data']:
            token = result['data']['token']
            return {
                'result': result,
                'token': token,
                'changed': False,
                'debug_info': debug_info
            }
        else:
            self.module.fail_json(
                msg="Login failed: no token found in response",
                debug_info=debug_info,
                response_structure=result
            )
    
    def _authenticated_request(self, endpoint, token, method='POST', data=None):
        """Make authenticated request with token"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        result, info, debug_info = self._make_request(endpoint, method=method, data=data, headers=headers)
        return {'result': result, 'changed': True, 'debug_info': debug_info}
    
    def enable_nodered(self, token, parameters):
        """Toggle Node-RED service"""
        return self._authenticated_request('/services/node-red/start', token, data=parameters)

    def disable_nodered(self, token, parameters):
        """Toggle Node-RED service"""
        return self._authenticated_request('/services/node-red/stop', token, data=parameters)
    
    def get_nodered_token(self, username, password):
        """Get Node-RED authentication token from port 1880"""
        import json
        from ansible.module_utils.urls import fetch_url
        
        # Node-RED runs on port 1880
        protocol = 'https' if self.use_https else 'http'
        nodered_url = f"{protocol}://{self.host}:1880/auth/token"
        
        # Node-RED authentication payload
        auth_data = {
            'client_id': 'node-red-admin',
            'grant_type': 'password',
            'scope': '*',
            'username': username,
            'password': password
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        debug_info = {
            'step': 'node_red_auth',
            'url': nodered_url,
            'username': username
        }
        
        try:
            resp, info = fetch_url(
                self.module,
                nodered_url,
                data=json.dumps(auth_data),
                headers=headers,
                method='POST',
                timeout=self.timeout
            )
            
            if info['status'] != 200:
                debug_info['error'] = f"Node-RED auth failed: {info['status']} {info.get('msg', '')}"
                return {
                    'result': {'error': debug_info['error']},
                    'changed': False,
                    'debug_info': debug_info
                }
            
            response_data = json.loads(resp.read())
            access_token = response_data.get('access_token')
            
            if not access_token:
                debug_info['error'] = "No access token in Node-RED response"
                return {
                    'result': {'error': debug_info['error']},
                    'changed': False,
                    'debug_info': debug_info
                }
                
            return {
                'result': {
                    'access_token': access_token,
                    'token_type': response_data.get('token_type', 'Bearer'),
                    'message': 'Node-RED authentication successful'
                },
                'token': access_token,
                'changed': False,
                'debug_info': debug_info
            }
            
        except Exception as e:
            debug_info['error'] = f"Node-RED authentication exception: {str(e)}"
            return {
                'result': {'error': debug_info['error']},
                'changed': False,
                'debug_info': debug_info
            }

    def backup_nodered(self, token, parameters):
        """Backup Node-RED flows using Node-RED API on port 1880"""
        import json
        from datetime import datetime
        from ansible.module_utils.urls import fetch_url
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting Node-RED flows from port 1880 API")
        
        # Node-RED runs on port 1880
        protocol = 'https' if self.use_https else 'http'
        flows_url = f"{protocol}://{self.host}:1880/flows"
        
        # Get Node-RED auth token (assuming it's passed in parameters)
        nodered_token = parameters.get('nodered_token')
        if not nodered_token:
            # Try to use the provided token as Node-RED token for now
            nodered_token = token
            debug_info['messages'].append("Using provided token for Node-RED API")
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {nodered_token}'
            }
            
            resp, info = fetch_url(
                self.module,
                flows_url,
                headers=headers,
                method='GET',
                timeout=self.timeout
            )
            
            if info['status'] == 200:
                flows_data = json.loads(resp.read())
                debug_info['messages'].append("Successfully retrieved Node-RED flows from API")
                debug_info['api_success'] = True
                config_data = {
                    'flows': flows_data,
                    'version': '1.0',  # Could be extracted from Node-RED settings if available
                    'exported_at': datetime.now().isoformat()
                }
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "Node-RED API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Could not retrieve Node-RED flows: HTTP {info['status']}"
                }
                debug_info['messages'].append("Node-RED API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "Node-RED API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call Node-RED API: {str(api_error)}"
            }
            debug_info['messages'].append(f"Node-RED API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning Node-RED flows data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'Node-RED flows retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_nodered(self, token, parameters):
        """Restore Node-RED flows using Node-RED API on port 1880"""
        import json
        from datetime import datetime
        from ansible.module_utils.urls import fetch_url
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received Node-RED flows data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Extract flows from config data
        flows_data = config_data.get('flows', config_data)  # Handle both wrapped and direct flow data
        
        # Node-RED runs on port 1880
        protocol = 'https' if self.use_https else 'http'
        flows_url = f"{protocol}://{self.host}:1880/flows"
        
        # Get Node-RED auth token (assuming it's passed in parameters)
        nodered_token = parameters.get('nodered_token')
        if not nodered_token:
            # Try to use the provided token as Node-RED token for now
            nodered_token = token
            debug_info['messages'].append("Using provided token for Node-RED API")
        
        # Send flows to Node-RED
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {nodered_token}'
            }
            
            resp, info = fetch_url(
                self.module,
                flows_url,
                data=json.dumps(flows_data),
                headers=headers,
                method='POST',
                timeout=self.timeout
            )
            
            if info['status'] in [200, 204]:  # Node-RED typically returns 204 for flow updates
                debug_info['messages'].append("Successfully sent Node-RED flows to API")
                debug_info['api_success'] = True
                
                return {
                    'result': {
                        'config_size': len(json.dumps(config_data)),
                        'message': 'Node-RED flows restored successfully',
                        'api_response': f"HTTP {info['status']}"
                    },
                    'changed': True,
                    'debug_info': debug_info
                }
            else:
                debug_info['messages'].append(f"Failed to restore Node-RED flows: HTTP {info['status']}")
                debug_info['api_success'] = False
                
                self.module.fail_json(
                    msg=f"Failed to restore Node-RED flows: HTTP {info['status']} {info.get('msg', '')}",
                    debug_info=debug_info
                )
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore Node-RED flows: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore Node-RED flows to device: {str(api_error)}",
                debug_info=debug_info
            )
    
    def upgrade_nodered(self, token, parameters):
        """Upgrade Node-RED"""
        return self._authenticated_request('/node-red/upgrade', token, data=parameters)
    
    def rollback_nodered(self, token, parameters):
        """Rollback Node-RED"""
        return self._authenticated_request('/node-red/downgrade', token, data=parameters)
    
    def deploy_node_red_flow(self, token, parameters):
        """Deploy Node-RED flow from library - POST to /node-red/deployFlow/:library_flow_name"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get required parameter
        library_flow_name = parameters.get('library_flow_name')
        if not library_flow_name:
            self.module.fail_json(
                msg="Parameter 'library_flow_name' is required for deploy_node_red_flow action",
                debug_info=debug_info
            )
        
        debug_info['messages'].append(f"Deploying Node-RED flow: {library_flow_name}")
        
        # Construct the endpoint with the flow name
        endpoint = f'/node-red/deployFlow/{library_flow_name}'
        
        # Send deployment request to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(endpoint, method='POST', data={}, headers=headers)
            
            debug_info['messages'].append(f"Successfully deployed Node-RED flow: {library_flow_name}")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'library_flow_name': library_flow_name,
                    'message': f'Node-RED flow "{library_flow_name}" deployed successfully',
                    'api_response': result,
                    'endpoint': endpoint
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to deploy Node-RED flow: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to deploy Node-RED flow '{library_flow_name}': {str(api_error)}",
                debug_info=debug_info
            )
    
    def change_password(self, token, parameters):
        """Change device password"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get required parameters
        old_password = parameters.get('old_password')
        new_password = parameters.get('new_password')
        username = parameters.get('username', 'tulip')  # Default to tulip
        
        if not old_password or not new_password:
            self.module.fail_json(
                msg="Both old_password and new_password are required for change_password action",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Hashing old and new passwords with device serial")
        
        # Use device name (inventory hostname) as serial number for hashing, same as login
        device_name = self.module.params.get('device_name', '')
        old_pass_hash = self._hash_password(old_password, device_name)
        new_pass_hash = self._hash_password(new_password, device_name)
        
        debug_info['messages'].append(f"Sending password change request for username: {username}")
        
        # Prepare data according to the API format shown in curl example
        data = {
            'old_pass': old_pass_hash,
            'new_pass': new_pass_hash,
            'username': username
        }
        
        # Make authenticated PUT request to /password endpoint
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/password', method='PUT', data=data, headers=headers)
            
            debug_info['messages'].append("Successfully sent password change request to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'message': 'Password changed successfully',
                    'username': username,
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to change password: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to change device password: {str(api_error)}",
                debug_info=debug_info
            )
    
    def gateway_factory_reset(self, token, parameters):
        """Perform factory reset"""
        return self._authenticated_request('/gateway/factory_Reset', token, data=parameters)

    def gateway_serial_number(self, token, parameters):
        """Perform factory reset"""
        return self._authenticated_request('/gateway/serialNumber', token, method='GET', data=parameters)

    def gateway_network_health_check(self, token, parameters):
        """Perform factory reset"""
        return self._authenticated_request('/gateway/networkHealthCheck', token, method='GET', data=parameters)

    def gateway_locate(self, token, parameters):
        """Physically locate gatewya"""
        return self._authenticated_request('/gateway/locate', token, method='GET', data=parameters)

    def gateway_device_info(self, token, parameters):
        """Gateway Device Information"""
        return self._authenticated_request('/gateway/deviceInfo', token, method='GET', data=parameters)

    def gateway_tulip_url(self, token, parameters):
        """Check if gateway is authenticated to tulip"""
        return self._authenticated_request('/gateway/factoryURL', token, method='GET', data=parameters)

    def gateway_tulip_auth(self, token, parameters):
        """Authenticate gateway to tulip"""
        return self._authenticated_request('/gateway/authenticate', token, data=parameters)

    def gateway_check_internet(self, token, parameters):
        """Check if gateway is online"""
        return self._authenticated_request('/gateway/check/internet', token, method='GET', data=parameters)

    def enable_mqtt_broker(self, token, parameters):
        """Toggle MQTT broker"""
        return self._authenticated_request('/mqtt/enable', token, data=parameters)
    
    def disable_mqtt_broker(self, token, parameters):
        """Toggle MQTT broker"""
        return self._authenticated_request('/mqtt/disable', token, data=parameters)
    
    def backup_mqtt_broker(self, token, parameters):
        """Backup MQTT broker configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/mqtt/config', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'MQTT broker configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }
    
    def restore_mqtt_broker(self, token, parameters):
        """Restore MQTT broker configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/mqtt/config', method='POST', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'MQTT broker configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore configuration to device: {str(api_error)}",
                debug_info=debug_info
            )
    
    def backup_mqtt_bridge(self, token, parameters):
        """Backup MQTT bridge configuration - GET list from /devconn and return all endpoints"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting devconn endpoints list from device API")
        
        # Get all device connections from /devconn endpoint
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/devconn', method='GET', headers=headers)
            
            if result:
                # The result has structure: {"data": {"configs": [...]}}
                # We'll store the full result structure for accurate restore
                config_data = result
                configs = result.get('data', {}).get('configs', []) if isinstance(result, dict) else []
                debug_info['messages'].append(f"Successfully retrieved {len(configs)} devconn endpoint configs from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve devconn endpoints from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning devconn endpoints data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'MQTT bridge devconn endpoints retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data,
                'endpoint_count': len(configs) if 'configs' in locals() and isinstance(configs, list) else 'unknown'
            },
            'changed': True,
            'debug_info': debug_info
        }
    
    def restore_mqtt_bridge(self, token, parameters):
        """Restore MQTT bridge configuration - POST entire config list to replace all devconn endpoints"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': [],
            'operations': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received devconn endpoints data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # If this is a placeholder/error backup, skip restore
        if isinstance(config_data, dict) and 'error' in config_data:
            debug_info['messages'].append("Skipping restore - backup contains error data")
            return {
                'result': {
                    'message': 'Skipped restore - backup contains error data',
                    'config_size': len(json.dumps(config_data)),
                    'operations_performed': []
                },
                'changed': False,
                'debug_info': debug_info
            }
        
        # Extract configs from the real API structure: {"data": {"configs": [...]}}
        configs_to_restore = []
        if isinstance(config_data, dict):
            if 'data' in config_data and 'configs' in config_data['data']:
                # Real API structure
                configs_to_restore = config_data['data']['configs']
                debug_info['messages'].append(f"Found {len(configs_to_restore)} configs in API data structure")
            elif 'configs' in config_data:
                # Direct configs structure (fallback)
                configs_to_restore = config_data['configs']
                debug_info['messages'].append(f"Found {len(configs_to_restore)} configs in direct structure")
            else:
                debug_info['messages'].append("No recognizable config structure found in backup data")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        try:
            # Step 1: Get current devconn endpoints (for comparison/logging)
            debug_info['messages'].append("Getting current devconn endpoints")
            current_result, info, api_debug = self._make_request('/devconn', method='GET', headers=headers)
            
            # Extract current configs from API response structure
            current_configs = []
            if isinstance(current_result, dict) and 'data' in current_result and 'configs' in current_result['data']:
                current_configs = current_result['data']['configs']
            debug_info['messages'].append(f"Found {len(current_configs)} current endpoint configs")
            
            # Step 2: Clean up configs for restore (remove IDs, server will assign new ones)
            clean_configs = []
            for config in configs_to_restore:
                clean_config = {k: v for k, v in config.items() if k != 'id'}
                clean_configs.append(clean_config)
                config_name = clean_config.get('mqtt', {}).get('name', 'unnamed') if 'mqtt' in clean_config else 'unnamed'
                debug_info['messages'].append(f"Prepared config for restore: {config_name}")
            
            # Step 3: POST entire config list to replace all (no individual operations needed)
            debug_info['messages'].append(f"Posting {len(clean_configs)} configs to /devconn to replace all")
            restore_data = {"configs": clean_configs}
            
            create_result, info, api_debug = self._make_request('/devconn', method='POST', data=restore_data, headers=headers)
            debug_info['operations'].append({
                'action': 'replace_all', 
                'configs_sent': len(clean_configs),
                'success': True,
                'api_response': create_result
            })
            
            debug_info['messages'].append("Successfully completed devconn endpoints restore")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'MQTT bridge devconn endpoints restored successfully',
                    'operations_performed': debug_info['operations'],
                    'configs_restored': len(clean_configs),
                    'configs_in_backup': len(configs_to_restore),
                    'current_configs_found': len(current_configs)
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore devconn endpoints: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore devconn endpoints: {str(api_error)}",
                debug_info=debug_info
            )

    def backup_lightkit(self, token, parameters):
        """Backup LightKit configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting LightKit config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/lightkit/config', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved LightKit config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve LightKit configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning LightKit config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'LightKit configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_lightkit(self, token, parameters):
        """Restore LightKit configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received LightKit config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))

        config_data["transient"] = False
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/lightkit/config', method='POST', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent LightKit config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'LightKit configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore LightKit config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore LightKit configuration to device: {str(api_error)}",
                debug_info=debug_info
            )
    
    def configure_network(self, token, parameters):
        """Configure network settings"""
        return self._authenticated_request('/network/configure', token, data=parameters)

    def backup_network_state(self, token, parameters):
        """Backup network state configuration - GET from /network/state and return config data"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting network state from device API")
        
        # Get network state from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/state', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved network state from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve network state from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning network state data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'Network state retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_network_config(self, token, parameters):
        """Restore network configuration - Receive config data and PUT to /network/config (REQUIRES CONFIRMATION)"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received network config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send network configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/config', method='PUT', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent network config to device API")
            debug_info['messages'].append("⚠️  IMPORTANT: Network configuration applied but requires CONFIRMATION within timeout period")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'Network configuration applied successfully - CONFIRMATION REQUIRED within timeout period to prevent revert',
                    'api_response': result,
                    'confirmation_required': True,
                    'warning': 'Configuration will revert automatically if not confirmed - use v0_confirm_network_config.yml'
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore network config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore network configuration to device: {str(api_error)}",
                debug_info=debug_info
            )

    def confirm_network_config(self, token, parameters):
        """Confirm network configuration changes - PUT to /network/config/confirm to prevent revert"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Confirming network configuration changes")
        
        # Send network configuration confirmation to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/config/confirm', method='PUT', data={}, headers=headers)
            
            debug_info['messages'].append("Successfully confirmed network configuration changes")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'message': 'Network configuration changes confirmed successfully - configuration will not revert',
                    'api_response': result,
                    'confirmation_status': 'confirmed'
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to confirm network configuration: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to confirm network configuration: {str(api_error)}",
                debug_info=debug_info
            )

    def backup_ntp(self, token, parameters):
        """Backup NTP configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting NTP config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/ntp', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved NTP config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve NTP configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning NTP config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'NTP configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_ntp(self, token, parameters):
        """Restore NTP configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received NTP config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/ntp', method='POST', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent NTP config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'NTP configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore NTP config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore NTP configuration to device: {str(api_error)}",
                debug_info=debug_info
            )

    def backup_http_proxy(self, token, parameters):
        """Backup HTTP proxy configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting HTTP proxy config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/proxy', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved HTTP proxy config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve HTTP proxy configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning HTTP proxy config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'HTTP proxy configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_http_proxy(self, token, parameters):
        """Restore HTTP proxy configuration - receive config data and PUT to device.

        The device returns 405 Method Not Allowed for POST on /network/proxy
        (Allow: GET,HEAD,PUT,DELETE). PUT is the correct verb for writes.
        """
        import json

        debug_info = {
            'step': 'starting',
            'messages': []
        }

        # Get config data from parameters (passed from Ansible). Accept either
        # a wrapped payload ({"data": {host, port, ...}}) or the unwrapped form
        # so backups from backup_http_proxy can be fed back without massaging.
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        if isinstance(config_data, dict) and 'data' in config_data and isinstance(config_data['data'], dict):
            config_data = config_data['data']

        debug_info['messages'].append("Received HTTP proxy config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(
                '/network/proxy', method='PUT', data=config_data, headers=headers
            )

            debug_info['messages'].append("Successfully sent HTTP proxy config to device API")
            debug_info['api_success'] = True

            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'HTTP proxy configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }

        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore HTTP proxy config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)

            self.module.fail_json(
                msg=f"Failed to restore HTTP proxy configuration to device: {str(api_error)}",
                debug_info=debug_info
            )

    def configure_http_proxy(self, token, parameters):
        """Configure HTTP proxy with direct parameters - PUT /network/proxy.

        Accepts {host, port, username, password} either at the top level of
        ``parameters`` (Ansible passes the module's `parameters:` dict
        directly) or wrapped under ``parameters.config_data``. This mirrors
        ``restore_http_proxy`` so the same module action can serve both
        roundtrips (golden-image restore) and direct provisioning.
        """
        import json

        debug_info = {
            'step': 'starting',
            'messages': []
        }

        if 'config_data' in parameters and isinstance(parameters['config_data'], dict):
            payload = parameters['config_data']
            if 'data' in payload and isinstance(payload['data'], dict):
                payload = payload['data']
        else:
            payload = {
                k: parameters[k]
                for k in ('host', 'port', 'username', 'password')
                if k in parameters
            }

        if not payload.get('host'):
            self.module.fail_json(
                msg="configure_http_proxy requires at least a 'host' parameter (and typically port/username/password).",
                debug_info=debug_info
            )

        debug_info['messages'].append("Configuring HTTP proxy on device")
        debug_info['config_size'] = len(json.dumps(payload))

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(
                '/network/proxy', method='PUT', data=payload, headers=headers
            )

            debug_info['messages'].append("Successfully sent HTTP proxy config to device API")
            debug_info['api_success'] = True

            return {
                'result': {
                    'config_size': len(json.dumps(payload)),
                    'message': 'HTTP proxy configured successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }

        except Exception as api_error:
            debug_info['messages'].append(f"Failed to configure HTTP proxy: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)

            self.module.fail_json(
                msg=f"Failed to configure HTTP proxy on device: {str(api_error)}",
                debug_info=debug_info
            )

    def clear_http_proxy(self, token, parameters):
        """Clear http proxy settings"""
        return self._authenticated_request('/network/proxy', token, method='DELETE', data=parameters)

    def backup_network_certificates(self, token, parameters):
        """Backup network certificates configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting network certificates config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/certificate', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved network certificates config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve network certificates configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning network certificates config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'Network certificates configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_network_certificates(self, token, parameters):
        """Restore network certificates configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received network certificates config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/certificate', method='POST', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent network certificates config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'Network certificates configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore network certificates config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore network certificates configuration to device: {str(api_error)}",
                debug_info=debug_info
            )

    def clear_network_certificates(self, token, parameters):
        """Clear Root Certs"""
        return self._authenticated_request('/network/certificate/all', token, method='DELETE', data=parameters)

    def backup_root_certs(self, token, parameters):
        """Backup root certs - GET /security/root-certs and return config data for local persistence."""
        import json
        from datetime import datetime

        debug_info = {
            'step': 'starting',
            'messages': []
        }

        debug_info['messages'].append("Getting root certs from device API (/security/root-certs)")

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(
                '/security/root-certs', method='GET', headers=headers
            )

            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved root certs from device API")
                debug_info['api_success'] = True
            else:
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve root certs from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False

        except Exception as api_error:
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)

        debug_info['messages'].append("Returning root certs data to Ansible for local file writing")

        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'Root certs retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_root_certs(self, token, parameters):
        """Restore root certs - receive config data from Ansible and POST to /security/root-certs."""
        import json

        debug_info = {
            'step': 'starting',
            'messages': []
        }

        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )

        debug_info['messages'].append("Received root certs config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(
                '/security/root-certs', method='POST', data=config_data, headers=headers
            )

            debug_info['messages'].append("Successfully sent root certs to device API")
            debug_info['api_success'] = True

            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'Root certs restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }

        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore root certs: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)

            self.module.fail_json(
                msg=f"Failed to restore root certs to device: {str(api_error)}",
                debug_info=debug_info
            )

    def backup_https(self, token, parameters):
        """Backup HTTPS configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting HTTPS config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/portal/security', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved HTTPS config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve HTTPS configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning HTTPS config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'HTTPS configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_https(self, token, parameters):
        """Restore HTTPS configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )

        config_data = {"portalSecurityConfig": config_data}
        
        debug_info['messages'].append("Received HTTPS config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/portal/security', method='POST', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent HTTPS config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'HTTPS configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore HTTPS config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore HTTPS configuration to device: {str(api_error)}",
                debug_info=debug_info
            )
    
    def backup_drivers(self, token, parameters):
        """Backup drivers configuration - GET from device and return config data"""
        import os
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting drivers config from device API")
        
        # Get configuration from device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/drivers', method='GET', headers=headers)
            
            if result:
                config_data = result
                debug_info['messages'].append("Successfully retrieved drivers config from device API")
                debug_info['api_success'] = True
            else:
                # If API call fails, create a placeholder backup for testing
                config_data = {
                    "note": "API call failed, placeholder backup created",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not retrieve drivers configuration from device"
                }
                debug_info['messages'].append("API call failed, using placeholder config")
                debug_info['api_success'] = False
                
        except Exception as api_error:
            # If API call fails, create a placeholder backup for testing
            config_data = {
                "note": "API call failed, placeholder backup created",
                "timestamp": datetime.now().isoformat(),
                "error": str(api_error),
                "debug_info": f"Failed to call API: {str(api_error)}"
            }
            debug_info['messages'].append(f"API call exception: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
        
        debug_info['messages'].append("Returning drivers config data to Ansible for local file writing")
        
        return {
            'result': {
                'config_data': config_data,
                'config_size': len(json.dumps(config_data)),
                'message': 'Drivers configuration retrieved successfully (will be written locally by Ansible)',
                'api_success': 'note' not in config_data
            },
            'changed': True,
            'debug_info': debug_info
        }

    def restore_drivers(self, token, parameters):
        """Restore drivers configuration - Receive config data and POST to device"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get config data from parameters (passed from Ansible)
        config_data = parameters.get('config_data')
        if not config_data:
            self.module.fail_json(
                msg="No config_data provided in parameters",
                debug_info=debug_info
            )
        
        debug_info['messages'].append("Received drivers config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/drivers', method='PUT', data=config_data, headers=headers)
            
            debug_info['messages'].append("Successfully sent drivers config to device API")
            debug_info['api_success'] = True
            
            return {
                'result': {
                    'config_size': len(json.dumps(config_data)),
                    'message': 'Drivers configuration restored successfully',
                    'api_response': result
                },
                'changed': True,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to restore drivers config to device: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to restore drivers configuration to device: {str(api_error)}",
                debug_info=debug_info
            )
    
    def manage_services(self, token, parameters):
        """Manage Tulip Edge device services - enable/disable services from supported list"""
        import json
        from datetime import datetime
        
        # List of supported services
        SUPPORTED_SERVICES = ["node-red", "snmpd", "tulip-connectorhost", "tulip-ap"]
        
        debug_info = {
            'step': 'starting',
            'messages': [],
            'operations': []
        }
        
        # Get required parameters
        services = parameters.get('services', [])
        action = parameters.get('action', '')  # 'enable' or 'disable'
        
        if not services:
            self.module.fail_json(
                msg="Parameter 'services' is required and must be a list of service names",
                debug_info=debug_info,
                supported_services=SUPPORTED_SERVICES
            )
            
        if action not in ['enable', 'disable']:
            self.module.fail_json(
                msg="Parameter 'action' must be either 'enable' or 'disable'",
                debug_info=debug_info,
                supported_services=SUPPORTED_SERVICES
            )
        
        # Validate services are supported
        invalid_services = [s for s in services if s not in SUPPORTED_SERVICES]
        if invalid_services:
            self.module.fail_json(
                msg=f"Unsupported services: {invalid_services}",
                debug_info=debug_info,
                supported_services=SUPPORTED_SERVICES,
                invalid_services=invalid_services
            )
        
        debug_info['messages'].append(f"Managing {len(services)} services: {services}")
        debug_info['messages'].append(f"Action: {action}")
        
        # Process each service
        successful_operations = []
        failed_operations = []
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        for service_id in services:
            try:
                # Determine endpoint based on action
                endpoint_action = 'start' if action == 'enable' else 'stop'
                endpoint = f'/services/{service_id}/{endpoint_action}'
                
                debug_info['messages'].append(f"Sending {action} request for service: {service_id}")
                
                # Make the API call
                result, info, api_debug = self._make_request(endpoint, method='POST', headers=headers)
                
                operation_result = {
                    'service_id': service_id,
                    'action': action,
                    'endpoint': endpoint,
                    'status': 'success',
                    'http_status': info.get('status'),
                    'response': result
                }
                
                successful_operations.append(operation_result)
                debug_info['operations'].append(operation_result)
                debug_info['messages'].append(f"Successfully {action}d service: {service_id}")
                
            except Exception as service_error:
                operation_result = {
                    'service_id': service_id,
                    'action': action,
                    'endpoint': f'/services/{service_id}/{endpoint_action}',
                    'status': 'failed',
                    'error': str(service_error)
                }
                
                failed_operations.append(operation_result)
                debug_info['operations'].append(operation_result)
                debug_info['messages'].append(f"Failed to {action} service {service_id}: {str(service_error)}")
        
        # Determine overall result
        if failed_operations and not successful_operations:
            # All operations failed
            self.module.fail_json(
                msg=f"All service {action} operations failed",
                debug_info=debug_info,
                failed_operations=failed_operations,
                successful_operations=successful_operations
            )
        elif failed_operations:
            # Some operations failed
            debug_info['messages'].append(f"Partial success: {len(successful_operations)} succeeded, {len(failed_operations)} failed")
            return {
                'result': {
                    'message': f'Partial success: {len(successful_operations)} services {action}d, {len(failed_operations)} failed',
                    'action': action,
                    'services_requested': services,
                    'successful_operations': successful_operations,
                    'failed_operations': failed_operations,
                    'total_requested': len(services),
                    'total_successful': len(successful_operations),
                    'total_failed': len(failed_operations)
                },
                'changed': len(successful_operations) > 0,
                'debug_info': debug_info
            }
        else:
            # All operations succeeded
            debug_info['messages'].append(f"All {len(services)} service {action} operations completed successfully")
            return {
                'result': {
                    'message': f'Successfully {action}d all {len(services)} services',
                    'action': action,
                    'services_requested': services,
                    'successful_operations': successful_operations,
                    'total_requested': len(services),
                    'total_successful': len(successful_operations)
                },
                'changed': True,
                'debug_info': debug_info
            }
    
    def get_supported_log_services(self, token, parameters):
        """Get list of supported services for logging from /logs/supportedservices endpoint"""
        import json
        from datetime import datetime
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        debug_info['messages'].append("Getting supported log services from device API")
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/logs/supportedservices', method='GET', headers=headers)
            
            debug_info['messages'].append("Successfully retrieved supported log services from device API")
            debug_info['api_success'] = True
            
            # Extract services list from response
            supported_services = result if isinstance(result, list) else result.get('services', result.get('data', []))
            
            return {
                'result': {
                    'supported_services': supported_services,
                    'total_services': len(supported_services) if isinstance(supported_services, list) else 0,
                    'message': 'Supported log services retrieved successfully',
                    'raw_response': result
                },
                'changed': False,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to retrieve supported log services: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to retrieve supported log services: {str(api_error)}",
                debug_info=debug_info
            )
    
    def get_logs(self, token, parameters):
        """Get logs from /logs endpoint with numLines and service query parameters"""
        import json
        from datetime import datetime
        from urllib.parse import urlencode
        
        debug_info = {
            'step': 'starting',
            'messages': []
        }
        
        # Get parameters for log retrieval
        service = parameters.get('service', '')
        num_lines = parameters.get('numLines', parameters.get('num_lines', 100))  # Support both naming conventions
        
        debug_info['messages'].append(f"Getting logs for service: '{service}' with numLines: {num_lines}")
        
        # Build query parameters
        query_params = {}
        if service:
            query_params['service'] = service
        if num_lines is not None:
            query_params['numLines'] = str(num_lines)
        
        # Construct endpoint with query parameters
        endpoint = '/logs'
        if query_params:
            endpoint += '?' + urlencode(query_params)
        
        debug_info['endpoint'] = endpoint
        debug_info['query_params'] = query_params
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request(endpoint, method='GET', headers=headers)
            
            debug_info['messages'].append("Successfully retrieved logs from device API")
            debug_info['api_success'] = True
            
            # Handle different response formats
            logs_data = result
            
            # Parse the actual API response structure: {"data": {"logMessages": [...], "serviceName": "...", "numLogMessages": N}}
            if isinstance(result, dict):
                if 'data' in result and isinstance(result['data'], dict):
                    # Extract from the correct API structure
                    data_section = result['data']
                    logs_content = data_section.get('logMessages', [])
                    service_name = data_section.get('serviceName', service if service else 'unknown')
                    actual_log_count = data_section.get('numLogMessages', len(logs_content))
                else:
                    # Fallback to other possible response structures
                    logs_content = result.get('logs', result.get('logMessages', result.get('content', result)))
                    service_name = service if service else 'unknown'
                    actual_log_count = None
            else:
                logs_content = result
                service_name = service if service else 'unknown'
                actual_log_count = None
            
            # Parse logs if they're a string
            if isinstance(logs_content, str):
                log_lines = logs_content.strip().split('\n') if logs_content else []
            elif isinstance(logs_content, list):
                log_lines = logs_content
            else:
                log_lines = [str(logs_content)] if logs_content else []
            
            return {
                'result': {
                    'logs': log_lines,
                    'log_count': len(log_lines),
                    'service_requested': service_name,
                    'service_from_response': service_name,
                    'num_lines_requested': num_lines,
                    'num_lines_from_response': actual_log_count,
                    'message': f'Retrieved {len(log_lines)} log lines from {service_name}',
                    'query_params': query_params,
                    'raw_response': logs_data
                },
                'changed': False,
                'debug_info': debug_info
            }
            
        except Exception as api_error:
            debug_info['messages'].append(f"Failed to retrieve logs: {str(api_error)}")
            debug_info['api_success'] = False
            debug_info['api_error'] = str(api_error)
            
            self.module.fail_json(
                msg=f"Failed to retrieve logs: {str(api_error)}",
                debug_info=debug_info
            )
    
    def check_login(self, token, parameters):
        """Check if login token is still valid"""
        return self._authenticated_request('/auth/loggedIn', token, method='GET', data=None)
    
    def get_status(self, token, parameters):
        """Get device status information"""
        return self._authenticated_request('/kado/status', token, method='GET', data=None)


def main():
    module_args = dict(
        host=dict(type='str', required=True),
        port=dict(type='int', required=False, default=80),
        use_https=dict(type='bool', required=False, default=False),
        action=dict(
            type='str',
            required=True,
            choices=[
                'register', 'login', 'check_login', 'get_status', 'enable_nodered', 'disable_nodered', 'backup_nodered',
                'restore_nodered', 'get_nodered_token', 'upgrade_nodered', 'rollback_nodered', 'deploy_node_red_flow',
                'change_password', 'factory_reset',
                'enable_mqtt_broker', 'disable_mqtt_broker',
                'backup_mqtt_broker', 'restore_mqtt_broker',
                'restore_mqtt_bridge', 'backup_mqtt_bridge', 
                'backup_lightkit', 'restore_lightkit',
                'backup_ntp', 'restore_ntp',
                'backup_http_proxy', 'restore_http_proxy',
                'backup_network_certificates', 'restore_network_certificates',
                'backup_https', 'restore_https',
                'configure_network', 'backup_network_state', 'restore_network_config', 'confirm_network_config',
                'restore_root_certs', 'backup_root_certs', 'toggle_http_proxy',
                'configure_http_proxy', 'configure_ntp', 'toggle_https',
                'configure_https', 'backup_drivers', 'restore_drivers',
                'gateway_factory_reset', 'gateway_serial_number', 'gateway_network_health_check',
                'gateway_locate', 'gateway_device_info', 'gateway_tulip_url',
                'gateway_tulip_auth', 'gateway_check_internet',
                'manage_services', 'get_logs', 'get_supported_log_services',
            ]
        ),
        username=dict(type='str', required=False, default='tulip'),
        password=dict(type='str', required=False, no_log=True),
        token=dict(type='str', required=False, no_log=True),
        device_name=dict(type='str', required=False, default=''),
        parameters=dict(type='dict', required=False, default={}),
        timeout=dict(type='int', required=False, default=30)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    try:
        api = TulipEdgeAPI(module)
        action = module.params['action']
        
        # Actions that don't require authentication
        if action == 'register':
            if not module.params.get('password'):
                module.fail_json(msg="Password is required for register action")
            result = api.register(module.params['password'])
            
        elif action == 'login':
            if not module.params.get('password'):
                module.fail_json(msg="Password is required for login action")
            result = api.login(module.params['username'], module.params['password'])
            
        elif action == 'get_nodered_token':
            if not module.params.get('password'):
                module.fail_json(msg="Password is required for get_nodered_token action")
            result = api.get_nodered_token(module.params['username'], module.params['password'])
            
        # Actions that require authentication
        else:
            token = module.params.get('token')
            if not token:
                module.fail_json(msg=f"Token is required for {action} action")
            
            parameters = module.params['parameters']
            method = getattr(api, action)
            result = method(token, parameters)
        
        module.exit_json(**result)
        
    except Exception as e:
        module.fail_json(
            msg=f"Module execution failed: {to_text(e)}",
            exception=traceback.format_exc()
        )


if __name__ == '__main__':
    main()
