# Check Login Functionality

The `check_login` action allows you to verify if a stored authentication token is still valid without performing any operations.

## Usage Examples

### 1. Basic Token Validation

```yaml
- name: Check if token is still valid
  tulip.edge.tulip_edge_api:
    host: "{{ ansible_host }}"
    action: check_login
    token: "{{ stored_token }}"
    device_name: "{{ inventory_hostname }}"
  register: result
```

### 2. Using the Check Login Playbook

```bash
# Check tokens for all devices
ansible-playbook -i inventory/production.yml \
  collections/ansible_collections/tulip/edge/playbooks/check_login.yml

# Check token for specific device
ansible-playbook -i inventory/production.yml \
  collections/ansible_collections/tulip/edge/playbooks/check_login.yml \
  -l edge-device-01
```

### 3. Using the Smart Check and Refresh Playbook

This playbook will automatically refresh tokens if they're invalid:

```bash
# Check and auto-refresh tokens for all devices
ansible-playbook -i inventory/production.yml \
  collections/ansible_collections/tulip/edge/playbooks/check_and_refresh_login.yml

# Check without auto-refresh (manual mode)
ansible-playbook -i inventory/production.yml \
  collections/ansible_collections/tulip/edge/playbooks/check_and_refresh_login.yml \
  -e tulip_edge_auto_refresh_tokens=false
```

### 4. Integration in Other Playbooks

You can use `check_login` as a pre-task in other playbooks:

```yaml
---
- name: My Operation Playbook
  hosts: tulip_edge_devices
  pre_tasks:
    - name: Verify token is valid
      tulip.edge.tulip_edge_api:
        host: "{{ ansible_host | default(inventory_hostname) }}"
        action: check_login
        token: "{{ tulip_auth_token }}"
        device_name: "{{ inventory_hostname }}"
      register: token_check
      when: tulip_auth_token is defined
      
    - name: Refresh token if needed
      include_tasks: tasks/refresh_token.yml
      when: tulip_auth_token is not defined or token_check.failed
      
  tasks:
    # Your main operations here
```

## Response Format

### Success Response
```json
{
  "changed": false,
  "result": {
    "data": {
      "description": "Token is valid",
      "valid": true,
      "expires_in": 3542
    }
  }
}
```

### Failure Response
```json
{
  "failed": true,
  "msg": "Login failed: HTTP 401 - Unauthorized",
  "debug_info": {
    "url": "http://192.168.1.100:80/api/v0/auth/check",
    "method": "GET",
    "status_code": 401,
    "response": {"error": "Invalid or expired token"}
  }
}
```

## Benefits

1. **Token Management**: Verify tokens before performing operations
2. **Automated Workflows**: Build robust automation with token validation
3. **Troubleshooting**: Quickly identify authentication issues
4. **Fleet Management**: Check token status across multiple devices
5. **Smart Refresh**: Automatically refresh expired tokens

## Testing

Run the test script to see it in action with real devices:

```bash
./testing/test_check_login.sh
```

**Note**: This requires real Tulip Edge devices. Update the test script with your device IPs and credentials.

The test will demonstrate:
- Checking when no token exists
- Validating tokens after login
- Auto-refresh functionality
- Direct module usage
