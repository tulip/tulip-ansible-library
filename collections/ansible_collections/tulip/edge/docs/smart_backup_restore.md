# Local File-Based Backup and Restore System

## Overview
The backup and restore functionality now works with local files, providing proper data persistence and management:

- **Backup**: GET configuration from device HTTP API → Save as local JSON file
- **Restore**: Read local JSON file → POST configuration to device HTTP API

## How It Works

### Backup Process
1. **API Call**: `GET /api/v0/mqtt/config` (or equivalent for each component)
2. **Local Storage**: Save response as structured JSON file in `./backups/` directory
3. **Metadata**: Each backup includes device name, timestamp, component type, and configuration data

### Restore Process  
1. **File Discovery**: Find backup files by device name pattern or specific filename
2. **Latest Selection**: Auto-select most recent backup if no specific file requested
3. **API Call**: `POST /api/v0/mqtt/config` with configuration from backup file

## File Structure

### Backup File Format
```json
{
  "device": "EIO-01-6B4FE843",
  "component": "mqtt-broker", 
  "timestamp": "2024-01-15T10:30:45.123456",
  "backup_name": "EIO-01-6B4FE843-mqtt-broker-1705312245.json",
  "config": {
    // Actual configuration data from device API
  }
}
```

### File Naming Convention
- **Auto-generated**: `{device_name}-{component}-{unix_timestamp}.json`
- **Examples**: 
  - `EIO-01-6B4FE843-mqtt-broker-1705312245.json`
  - `EDGE-DEVICE-01-nodered-1705312300.json`

## Usage Examples

### ✅ Updated Implementation (MQTT Broker)

#### Backup
```bash
# Auto-generated filename in ./backups/
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/backup_mqtt_broker.yml -l EIO-01-6B4FE843

# Custom backup directory
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/backup_mqtt_broker.yml -l EIO-01-6B4FE843 -e "mqtt_backup_dir=/path/to/backups"

# Custom backup name  
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/backup_mqtt_broker.yml -l EIO-01-6B4FE843 -e "mqtt_backup_name=pre-maintenance"
```

#### Restore
```bash
# Restore latest backup for device (default)
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/restore_mqtt_broker.yml -l EIO-01-6B4FE843

# Restore specific backup
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/restore_mqtt_broker.yml -l EIO-01-6B4FE843 -e "mqtt_backup_name=pre-maintenance"

# Custom backup directory
ansible-playbook collections/ansible_collections/tulip/edge/playbooks/restore_mqtt_broker.yml -l EIO-01-6B4FE843 -e "mqtt_backup_dir=/path/to/backups"
```

### Sample Output

#### Backup Output
```
TASK [Display operation result] 
ok: [EIO-01-6B4FE843] => {
    "msg": "MQTT Broker backup completed successfully\nDevice: EIO-01-6B4FE843\nBackup file: ./backups/EIO-01-6B4FE843-mqtt-broker-1705312245.json\nConfig size: 2048 bytes\nStatus: MQTT broker configuration backed up successfully"
}
```

#### Restore Output
```
TASK [Display operation result]
ok: [EIO-01-6B4FE843] => {
    "msg": "MQTT Broker restore completed successfully\nDevice: EIO-01-6B4FE843\nRestored from: ./backups/EIO-01-6B4FE843-mqtt-broker-1705312245.json\nOriginal device: EIO-01-6B4FE843\nBackup timestamp: 2024-01-15T10:30:45.123456\nStatus: MQTT broker configuration restored successfully"
}
```

## Benefits of This Approach

1. **Data Persistence**: Backups are stored as files, not just API responses
2. **Version Control**: Files can be committed to git for configuration tracking
3. **Cross-Device Restore**: Backup from one device can be applied to another
4. **Backup Management**: Easy to list, archive, or clean up old backups
5. **Disaster Recovery**: Backups persist even if devices are replaced
6. **Audit Trail**: Full timestamp and metadata for each backup

## Implementation Status

### ✅ Completed
- `backup_mqtt_broker` - GET `/mqtt/config` + save to file
- `restore_mqtt_broker` - Read file + POST `/mqtt/config`  

### 📋 Next Steps (Apply Same Pattern)
The following components need the same local file-based approach:
- `backup_nodered` → GET `/nodered/config` + save to file
- `restore_nodered` → Read file + POST `/nodered/config`
- `backup_mqtt_bridge` → GET `/mqtt/bridge/config` + save to file  
- `restore_mqtt_bridge` → Read file + POST `/mqtt/bridge/config`
- `backup_root_certs` → GET `/security/root-certs` + save to file
- `restore_root_certs` → Read file + POST `/security/root-certs`
- `backup_drivers` → GET `/drivers/config` + save to file
- `restore_drivers` → Read file + POST `/drivers/config`

## File Management Commands

```bash
# List all backups
ls -la backups/

# List backups for specific device
ls -la backups/EIO-01-6B4FE843-*

# List backups by component
ls -la backups/*-mqtt-broker-*

# View backup contents
cat backups/EIO-01-6B4FE843-mqtt-broker-1705312245.json | jq

# Clean up old backups (keep last 5 for each device/component)
# (Custom script needed)
```

This approach provides a much more robust and practical backup/restore system!
