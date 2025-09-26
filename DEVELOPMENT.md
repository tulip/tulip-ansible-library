# Local Development and Testing Guide

This guide helps you develop and test the Tulip Edge collection locally without requiring actual edge devices.

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install flask ansible
   ```

2. **Start the mock API server:**
   ```bash
   cd testing/
   python mock_api_server.py
   ```

3. **Run tests against localhost:**
   ```bash
   ansible-playbook tulip.edge.login -i testing/test_inventory.ini
   ```

## Mock API Server

The mock server (`testing/mock_api_server.py`) simulates a Tulip Edge device API for development:

### Features
- **Authentication**: Accepts any username/password, returns JWT-like tokens
- **Token Management**: Validates Bearer tokens, handles expiration
- **State Simulation**: Maintains in-memory device state (Node-RED, MQTT, etc.)
- **All Endpoints**: Supports all operations from the collection
- **Backup Storage**: Simulates backup/restore operations

### Starting the Server
```bash
cd testing/
python mock_api_server.py
```

Server runs on `http://localhost:8080` with endpoints:
- `POST /api/register` - Device registration
- `POST /api/login` - Authentication 
- `POST /api/nodered/*` - Node-RED operations
- `POST /api/mqtt/*` - MQTT operations
- `GET /api/status` - Current device state
- `POST /api/*` - All other operations (generic responses)

## Test Inventory

Use the provided test inventory (`testing/test_inventory.ini`):

```ini
[tulip_edge_devices]
localhost ansible_host=127.0.0.1

[tulip_edge_devices:vars]
edge_api_port=8080
edge_use_https=false
device_password=test123
```

## Running Tests

### 1. Authentication Tests
```bash
# Test registration (using full path)
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/register.yml -i testing/test_inventory.ini

# Test login (stores token)
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/login.yml -i testing/test_inventory.ini
```

### 2. Node-RED Tests
```bash
# Enable Node-RED
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/toggle_nodered.yml -i testing/test_inventory.ini -e nodered_state=true

# Create backup
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/backup_nodered.yml -i testing/test_inventory.ini -e nodered_backup_name=test-backup

# Check server status
curl http://localhost:8080/api/status
```

### 3. Full Workflow Test
```bash
# Complete workflow
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/login.yml -i testing/test_inventory.ini
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/backup_nodered.yml -i testing/test_inventory.ini -e nodered_backup_name=dev-test
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/toggle_nodered.yml -i testing/test_inventory.ini -e nodered_state=false
ansible-playbook ~/.ansible/collections/ansible_collections/tulip/edge/playbooks/restore_nodered.yml -i testing/test_inventory.ini -e nodered_backup_name=dev-test
```

## Manual API Testing

Test the mock server directly with curl:

```bash
# Register device
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{"password": "test123"}'

# Login and get token
TOKEN=$(curl -X POST http://localhost:8080/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "tulip", "password": "test123"}' | jq -r '.token')

# Use token for operations
curl -X POST http://localhost:8080/api/nodered/toggle \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"enabled": true}'

# Check device status
curl http://localhost:8080/api/status
```

## Development Workflow

### 1. Modify Collection Code
```bash
# Edit module or playbooks
vim collections/ansible_collections/tulip/edge/plugins/modules/tulip_edge_api.py
vim collections/ansible_collections/tulip/edge/playbooks/login.yml
```

### 2. Test Changes
```bash
# Rebuild collection
make build

# Install locally for testing
ansible-galaxy collection install build/tulip-edge-1.0.0.tar.gz --force

# Run tests
ansible-playbook tulip.edge.login -i testing/test_inventory.ini -vvv
```

### 3. Debug Issues
```bash
# Verbose output
ansible-playbook tulip.edge.login -i testing/test_inventory.ini -vvv

# Check mock server logs (server prints all requests)
# Server shows: POST /api/login {"username": "tulip", "password": "test123"}

# Inspect module directly
ansible localhost -m tulip.edge.tulip_edge_api -a "host=localhost port=8080 action=login username=tulip password=test123"
```

## Testing Multiple Devices

Simulate a fleet by adding multiple localhost entries:

```ini
# testing/fleet_inventory.ini
[tulip_edge_devices]
device1 ansible_host=127.0.0.1 edge_api_port=8080
device2 ansible_host=127.0.0.1 edge_api_port=8081  
device3 ansible_host=127.0.0.1 edge_api_port=8082

[tulip_edge_devices:vars]
device_password=test123
```

Start multiple mock servers:
```bash
# Terminal 1
python mock_api_server.py  # runs on port 8080

# Terminal 2  
PORT=8081 python mock_api_server.py

# Terminal 3
PORT=8082 python mock_api_server.py
```

Test parallel operations:
```bash
ansible-playbook tulip.edge.login -i testing/fleet_inventory.ini
ansible-playbook tulip.edge.backup_nodered -i testing/fleet_inventory.ini -e nodered_backup_name=fleet-test
```

## Module Unit Testing

Test the module directly without playbooks:

```python
# testing/test_module.py
import sys
sys.path.insert(0, '../collections/ansible_collections/tulip/edge/plugins/modules')

from tulip_edge_api import TulipEdgeAPI
from ansible.module_utils.basic import AnsibleModule

# Mock module for testing
class MockModule:
    def __init__(self):
        self.params = {
            'host': 'localhost',
            'port': 8080,
            'use_https': False,
            'timeout': 30
        }
    
    def fail_json(self, **kwargs):
        print(f"FAIL: {kwargs}")
        
# Test API class
api = TulipEdgeAPI(MockModule())
print("API initialized successfully")
```

## CI/CD Testing

For automated testing, start the mock server in background:

```bash
# In CI script
python testing/mock_api_server.py &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Run all tests
make test-local

# Cleanup
kill $SERVER_PID
```

## Troubleshooting

### Common Issues

1. **"Connection refused"**
   - Ensure mock server is running: `python testing/mock_api_server.py`
   - Check port is available: `netstat -ln | grep 8080`

2. **"Authentication required"**
   - Run login playbook first: `ansible-playbook tulip.edge.login -i testing/test_inventory.ini`
   - Check token was cached: `ansible-inventory -i testing/test_inventory.ini --host localhost`

3. **"Module not found"**
   - Install collection: `ansible-galaxy collection install build/tulip-edge-1.0.0.tar.gz --force`
   - Check installation: `ansible-galaxy collection list tulip.edge`

4. **Import errors in module**
   - Check Python path: `python -c "import ansible.module_utils.basic"`
   - Install Ansible: `pip install ansible`

### Debug Commands

```bash
# Test module import
python -c "from ansible_collections.tulip.edge.plugins.modules.tulip_edge_api import main"

# Check collection installation
ansible-galaxy collection list | grep tulip

# Verify inventory parsing
ansible-inventory -i testing/test_inventory.ini --list

# Test connectivity
curl http://localhost:8080/api/status
```

## Production Testing

Before deploying to real devices:

1. **Test with real device credentials** in a staging environment
2. **Verify network connectivity** and firewall rules  
3. **Test error scenarios** (network timeouts, auth failures)
4. **Validate backup/restore** operations with real data
5. **Test parallel execution** at expected scale

Use `--limit` and `--check` for safe testing:
```bash
# Test on one device first
ansible-playbook tulip.edge.login -i production_inventory.ini --limit edge-device-001

# Dry run mode
ansible-playbook tulip.edge.backup_nodered -i production_inventory.ini --check
```
