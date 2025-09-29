# Network Configuration Management

## Overview
The network configuration management system provides safe backup, restore, and confirmation workflows for Tulip Edge device network settings. This implementation includes automatic rollback protection to prevent network lockouts.

- **Backup**: GET network state from `/network/state` → Save as local JSON file
- **Restore**: Read local JSON file → PUT configuration to `/network/config` (requires confirmation)
- **Confirm**: PUT to `/network/config/confirm` → Commit changes and prevent auto-revert

## How It Works

### Backup Process
1. **API Call**: `GET /network/state` to retrieve current network configuration
2. **Local Storage**: Save response as timestamped JSON file in `./network-backups/` directory  
3. **Metadata**: Each backup includes device name, timestamp, and full network state

### Restore Process (Two-Stage with Safety)
1. **File Loading**: Read backup file and validate JSON structure
2. **Configuration Apply**: `PUT /network/config` with configuration data
3. **Confirmation Required**: Changes will auto-revert unless confirmed within timeout period
4. **Safety Net**: Device automatically reverts to previous config if confirmation not received

### Confirmation Process
1. **Commit Changes**: `PUT /network/config/confirm` to make changes permanent
2. **Prevent Revert**: Stops automatic rollback timer
3. **Configuration Locked**: New configuration becomes the stable state

## File Structure

### Backup File Format
```json
{
  "interfaces": {
    "eth0": {
      "method": "static",
      "address": "192.168.1.100",
      "netmask": "255.255.255.0",
      "gateway": "192.168.1.1"
    }
  },
  "dns": {
    "nameservers": ["8.8.8.8", "8.8.4.4"]
  },
  "routing": {
    // routing configuration
  }
}
```

### File Naming Convention
- **Auto-generated**: `{device_name}_network_state_{unix_timestamp}.json`
- **Examples**:
  - `EIO-01-6B4FE843_network_state_1705312245.json`
  - `EDGE-DEVICE-01_network_state_1705312300.json`

## Playbook Usage

### 1. Network State Backup (`v0_backup_network_state.yml`)

#### Basic Backup
```bash
# Backup network state from all devices  
ansible-playbook tulip.edge.v0_backup_network_state -i inventory

# Backup single device
ansible-playbook tulip.edge.v0_backup_network_state -l EIO-01-6B4FE843 -i inventory

# Custom backup directory
ansible-playbook tulip.edge.v0_backup_network_state -i inventory -e "network_backup_dir=/path/to/backups"
```

#### Sample Output
```
TASK [Display backup summary]
ok: [EIO-01-6B4FE843] => {
    "msg": "Network State Backup Summary for EIO-01-6B4FE843:\n- Status: Success\n- Config size: 2048 bytes\n- Backup file: ./network-backups/EIO-01-6B4FE843_network_state_1705312245.json\n- Timestamp: 2024-01-15T10:30:45Z"
}
```

### 2. Network Configuration Restore (`v0_restore_network_config.yml`)

#### Basic Restore
```bash
# Restore from specific backup file
ansible-playbook tulip.edge.v0_restore_network_config -i inventory -e "config_file=/path/to/backup.json"

# Restore using backup directory pattern  
ansible-playbook tulip.edge.v0_restore_network_config -l EIO-01-6B4FE843 -i inventory -e "config_file=./network-backups/EIO-01-6B4FE843_network_state_1705312245.json"
```

#### Sample Output
```
TASK [Display restore results]
ok: [EIO-01-6B4FE843] => {
    "msg": "Network Configuration Restore Results for EIO-01-6B4FE843:\n- Status: Success\n- Operation ID: net-restore-1705312500\n- Confirmation required: true\n- Auto-revert timeout: 300 seconds\n\n⚠️  NEXT STEP: Run confirmation playbook to commit changes!\nCommand: ansible-playbook v0_confirm_network_config.yml -i inventory"
}
```

### 3. Network Configuration Confirmation (`v0_confirm_network_config.yml`)

#### Confirm Changes
```bash
# Confirm network changes (run immediately after restore)
ansible-playbook tulip.edge.v0_confirm_network_config -i inventory

# Confirm for specific device
ansible-playbook tulip.edge.v0_confirm_network_config -l EIO-01-6B4FE843 -i inventory
```

#### Sample Output
```
TASK [Display success message]
ok: [EIO-01-6B4FE843] => {
    "msg": "✅ Network configuration changes confirmed for EIO-01-6B4FE843\n🔒 Configuration is now committed and will not auto-revert"
}
```

## Complete Workflow Examples

### Standard Backup and Restore Workflow
```bash
# 1. Login to devices first
ansible-playbook tulip.edge.v0_edge_login -i inventory

# 2. Backup current network state (safety first!)
ansible-playbook tulip.edge.v0_backup_network_state -i inventory

# 3. Apply new network configuration (requires confirmation)
ansible-playbook tulip.edge.v0_restore_network_config -i inventory \
  -e "config_file=./network-backups/EIO-01-6B4FE843_network_state_1705312245.json"

# 4. Confirm changes immediately (prevents auto-revert)
ansible-playbook tulip.edge.v0_confirm_network_config -i inventory
```

### Device Migration Workflow
```bash
# 1. Backup from source device
ansible-playbook tulip.edge.v0_backup_network_state -l source-device -i inventory

# 2. Restore to target device
ansible-playbook tulip.edge.v0_restore_network_config -l target-device -i inventory \
  -e "config_file=./network-backups/source-device_network_state_1705312245.json"

# 3. Test connectivity (ensure you can reach target device)

# 4. Confirm if working, otherwise let it auto-revert
ansible-playbook tulip.edge.v0_confirm_network_config -l target-device -i inventory
```

## Safety Features

### ⚠️ Auto-Revert Protection
- **Timeout Period**: Network changes automatically revert after timeout (typically 5 minutes)
- **Safety Net**: Prevents permanent lockout from network configuration errors
- **Recovery**: Device returns to last known working configuration
- **Manual Recovery**: Physical access allows recovery if needed

### 🔒 Confirmation Requirements  
- **Two-Stage Process**: Apply configuration → Confirm changes
- **Explicit Confirmation**: Changes must be explicitly committed
- **Visual Warnings**: Clear indicators about confirmation requirements
- **Operation Tracking**: Each restore operation gets unique ID for tracking

### 📁 Backup Management
- **Timestamped Files**: Each backup includes creation timestamp
- **Device-Specific**: Backups clearly identify source device  
- **JSON Format**: Human-readable and version-control friendly
- **Directory Organization**: Centralized backup storage with clear naming

## Configuration Variables

```yaml
# Network configuration variables (group_vars/all.yml)
edge_api_port: 80                     # API port (default: 80)
edge_use_https: false                 # Use HTTPS (default: false)
edge_api_timeout: 30                  # Request timeout (default: 30s)
network_backup_dir: ./network-backups # Backup directory (default: ./network-backups)

# Example inventory variables
tulip_edge_devices:
  hosts:
    EIO-01-6B4FE843:
      ansible_host: 192.168.1.100
      edge_api_port: 80
    EDGE-DEVICE-02:
      ansible_host: 10.0.1.50
      edge_use_https: true
      edge_api_port: 443
```

## API Endpoints Reference

| Playbook | Method | Endpoint | Purpose | Requires Auth |
|----------|--------|----------|---------|---------------|
| **Backup** | GET | `/network/state` | Retrieve current network configuration | ✅ Yes |
| **Restore** | PUT | `/network/config` | Apply new network configuration | ✅ Yes |
| **Confirm** | PUT | `/network/config/confirm` | Commit configuration changes | ✅ Yes |

## Error Handling & Troubleshooting

### Common Error Scenarios

#### Authentication Errors
```
TASK [Check for authentication token] 
fatal: [EIO-01-6B4FE843]: FAILED! => {
    "msg": "Authentication token not found. Please run login playbook first."
}
```
**Solution**: Run `ansible-playbook tulip.edge.v0_edge_login -i inventory`

#### Missing Configuration File
```
TASK [Check for configuration file parameter]
fatal: [EIO-01-6B4FE843]: FAILED! => {
    "msg": "Configuration file path required. Set with: -e config_file=/path/to/backup.json"
}
```
**Solution**: Specify config file with `-e config_file=path/to/backup.json`

#### Network Connectivity Loss
```
TASK [Execute restore_network_config]
fatal: [EIO-01-6B4FE843]: FAILED! => {
    "msg": "Connection timeout - device may be unreachable"
}
```
**Recovery**: 
1. Wait for auto-revert timeout period (typically 5 minutes)
2. Device should revert to previous working configuration  
3. Try connecting with previous network settings
4. Physical access may be required if auto-revert fails

#### Confirmation Failure  
```
TASK [Display failure message]
ok: [EIO-01-6B4FE843] => {
    "msg": "❌ Failed to confirm network configuration for EIO-01-6B4FE843\nError: No pending configuration changes\n⚠️  WARNING: Configuration may auto-revert if not confirmed!"
}
```
**Possible Causes**:
- No pending changes to confirm
- Configuration already auto-reverted  
- Device connectivity issues
- Confirmation timeout expired

### Recovery Procedures

#### If Network Configuration Breaks Connectivity
1. **Wait for Auto-Revert**: Most configurations will revert automatically within 5 minutes
2. **Check Physical Access**: Ensure you can physically access the device if needed
3. **Verify Revert**: After timeout, device should be accessible with previous settings
4. **Manual Recovery**: Use console/physical access if auto-revert fails

#### If Backup Files Are Corrupted
1. **Validate JSON**: Use `jq` to check file structure: `cat backup.json | jq .`
2. **Manual Inspection**: Review backup file contents for obvious errors
3. **Fresh Backup**: Create new backup from working device
4. **Version Control**: Use git to track backup file changes

## Best Practices

### 🛡️ Safety First
1. **Always Backup First**: Create backup before any network changes
2. **Test Connectivity**: Verify you can reach device after changes
3. **Confirm Promptly**: Run confirmation immediately after successful restore
4. **Monitor Auto-Revert**: Be aware of timeout periods and plan accordingly
5. **Physical Access**: Ensure physical access is available before critical changes

### 📁 File Management
1. **Organize Backups**: Use consistent backup directory structure
2. **Version Control**: Store backup files in git for change tracking  
3. **Cleanup Policy**: Establish retention policy for old backups
4. **Documentation**: Document significant configuration changes
5. **Cross-Device Testing**: Test backups on non-production devices first

### 🔧 Operational Workflow  
1. **Staging Environment**: Test network changes in staging first
2. **Change Windows**: Plan network changes during maintenance windows
3. **Rollback Plan**: Always have tested rollback procedure ready
4. **Team Coordination**: Communicate network changes to relevant teams
5. **Monitoring**: Monitor device connectivity after configuration changes

## File Management Commands

```bash
# List all network backups
ls -la network-backups/

# List backups for specific device  
ls -la network-backups/EIO-01-6B4FE843_*

# View backup contents (pretty-printed JSON)
cat network-backups/EIO-01-6B4FE843_network_state_1705312245.json | jq

# Validate backup file JSON structure
jq empty network-backups/EIO-01-6B4FE843_network_state_1705312245.json && echo "Valid JSON" || echo "Invalid JSON"

# Find most recent backup for device
ls -t network-backups/EIO-01-6B4FE843_* | head -1

# Archive old backups (keep last 5 per device)
for device in $(ls network-backups/ | cut -d'_' -f1-3 | sort -u); do
  ls -t network-backups/${device}_* | tail -n +6 | xargs -r mv -t archive/
done

# Compare two backup files
diff <(jq -S . backup1.json) <(jq -S . backup2.json)

# Extract specific configuration section
jq '.interfaces.eth0' network-backups/device_backup.json
```

## Implementation Status

### ✅ Completed
- **Python API Methods**: `backup_network_state`, `restore_network_config`, `confirm_network_config`
- **Backup Playbook**: `v0_backup_network_state.yml` - GET `/network/state` + save to file
- **Restore Playbook**: `v0_restore_network_config.yml` - Read file + PUT `/network/config`  
- **Confirm Playbook**: `v0_confirm_network_config.yml` - PUT `/network/config/confirm`
- **Safety Features**: Auto-revert protection, confirmation workflow, comprehensive error handling
- **Documentation**: Complete usage guide, troubleshooting, and best practices

### 🔄 Integration Points
- **Authentication**: Integrates with existing `v0_edge_login.yml` authentication workflow
- **File System**: Uses consistent backup directory structure with other backup systems
- **Error Handling**: Follows collection-wide error handling patterns
- **Parallel Execution**: Supports multiple device operations using Ansible `strategy: free`

This network configuration management system provides enterprise-grade safety and reliability for managing Tulip Edge device network settings!
