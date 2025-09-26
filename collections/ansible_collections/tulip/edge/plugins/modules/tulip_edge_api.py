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
        
    def _make_request(self, endpoint, method='GET', data=None, headers=None):
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
        data = {'password': hashed_password}
        result, info, debug_info = self._make_request('/password', method='POST', data=data)
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
    
#     def backup_nodered(self, token, parameters):
#         """Backup Node-RED configuration"""
#         return self._authenticated_request('/node-red/backup', token, data=parameters)
#
#     def restore_nodered(self, token, parameters):
#         """Restore Node-RED configuration"""
#         return self._authenticated_request('/nodered/restore', token, data=parameters)
    
    def upgrade_nodered(self, token, parameters):
        """Upgrade Node-RED"""
        return self._authenticated_request('/node-red/upgrade', token, data=parameters)
    
    def rollback_nodered(self, token, parameters):
        """Rollback Node-RED"""
        return self._authenticated_request('/node-red/downgrade', token, data=parameters)
    
    def change_password(self, token, parameters):
        """Change device password"""
        return self._authenticated_request('/auth/change-password', token, data=parameters)
    
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
        """Restore HTTP proxy configuration - Receive config data and POST to device"""
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
        
        debug_info['messages'].append("Received HTTP proxy config data from Ansible")
        debug_info['config_size'] = len(json.dumps(config_data))
        
        # Send configuration to device
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            result, info, api_debug = self._make_request('/network/proxy', method='POST', data=config_data, headers=headers)
            
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
    
    def check_login(self, token, parameters):
        """Check if login token is still valid"""
        return self._authenticated_request('/auth/loggedIn', token, method='GET', data=None)


def main():
    module_args = dict(
        host=dict(type='str', required=True),
        port=dict(type='int', required=False, default=80),
        use_https=dict(type='bool', required=False, default=False),
        action=dict(
            type='str',
            required=True,
            choices=[
                'register', 'login', 'check_login', 'enable_nodered', 'disable_nodered', 'backup_nodered',
                'restore_nodered', 'upgrade_nodered', 'rollback_nodered',
                'change_password', 'factory_reset',
                'enable_mqtt_broker', 'disable_mqtt_broker',
                'backup_mqtt_broker', 'restore_mqtt_broker',
                'restore_mqtt_bridge', 'backup_mqtt_bridge', 
                'backup_lightkit', 'restore_lightkit',
                'backup_ntp', 'restore_ntp',
                'backup_http_proxy', 'restore_http_proxy',
                'backup_network_certificates', 'restore_network_certificates',
                'backup_https', 'restore_https',
                'configure_network',
                'restore_root_certs', 'backup_root_certs', 'toggle_http_proxy',
                'configure_http_proxy', 'configure_ntp', 'toggle_https',
                'configure_https', 'backup_drivers', 'restore_drivers',
                'gateway_factory_reset', 'gateway_serial_number', 'gateway_network_health_check',
                'gateway_locate', 'gateway_device_info', 'gateway_tulip_url',
                'gateway_tulip_auth', 'gateway_check_internet'
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
