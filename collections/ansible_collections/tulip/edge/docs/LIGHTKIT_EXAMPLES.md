# LightKit Backup and Restore Examples

This document provides usage examples for the new LightKit backup and restore functionality in the Tulip Edge Ansible collection.

## Basic Usage

### Backup LightKit Configuration

```bash
# Login to device first
ansible-playbook tulip.edge.login --limit device-name

# Backup LightKit configuration
ansible-playbook tulip.edge.backup_lightkit --limit device-name
```

### Restore LightKit Configuration

```bash
# Restore latest LightKit backup
ansible-playbook tulip.edge.restore_lightkit --limit device-name

# Restore specific LightKit backup
ansible-playbook tulip.edge.restore_lightkit \
  --limit device-name \
  -e lightkit_backup_name="device-name-lightkit-20241219-143022"
```

## Golden Device Provisioning with LightKit

### Complete Device Provisioning including LightKit

```bash
# 1. Backup all components from golden device including LightKit
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
ansible-playbook tulip.edge.backup_mqtt_bridge --limit golden-device
ansible-playbook tulip.edge.backup_drivers --limit golden-device
ansible-playbook tulip.edge.backup_root_certs --limit golden-device
ansible-playbook tulip.edge.backup_lightkit --limit golden-device

# 2. Deploy all components to new devices including LightKit
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit newly_provisioned \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-143022"

ansible-playbook tulip.edge.restore_mqtt_bridge \
  --limit newly_provisioned \
  -e mqtt_bridge_backup_name="golden-device-mqtt-bridge-20241219-143025"

ansible-playbook tulip.edge.restore_drivers \
  --limit newly_provisioned \
  -e drivers_backup_name="golden-device-drivers-20241219-143028"

ansible-playbook tulip.edge.restore_root_certs \
  --limit newly_provisioned \
  -e root_certs_backup_name="golden-device-root-certs-20241219-143030"

ansible-playbook tulip.edge.restore_lightkit \
  --limit newly_provisioned \
  -e lightkit_backup_name="golden-device-lightkit-20241219-143032"

# 3. Authenticate and verify
ansible-playbook tulip.edge.gateway_tulip_auth --limit newly_provisioned
ansible-playbook tulip.edge.gateway_device_info --limit newly_provisioned
```

## Working with LightKit Backups

### List Available LightKit Backups

```bash
# List all LightKit backups
ls -la backups/ | grep lightkit

# List LightKit backups for specific device
ls -la backups/ | grep device-name-lightkit

# Get latest LightKit backup for device
ls -t backups/device-name-lightkit-*.json | head -1
```

### Backup File Naming

LightKit backups follow the same naming convention as other components:
- **File format**: `<device>-lightkit-<timestamp>.json`
- **Variable format**: `<device>-lightkit-<timestamp>` (without .json extension)

### Custom Backup Names

```bash
# Create named backup
ansible-playbook tulip.edge.backup_lightkit \
  --limit golden-device \
  -e lightkit_backup_name="golden-device-lightkit-stable-v1.0"

# Deploy named backup
ansible-playbook tulip.edge.restore_lightkit \
  --limit production_devices \
  -e lightkit_backup_name="golden-device-lightkit-stable-v1.0"
```

## Advanced LightKit Scenarios

### Selective LightKit Updates

Update only LightKit configuration without affecting other components:

```bash
# Backup latest LightKit configuration from golden device
ansible-playbook tulip.edge.backup_lightkit --limit golden-device

# Deploy only LightKit to target devices
ansible-playbook tulip.edge.restore_lightkit \
  --limit target_devices \
  -e lightkit_backup_name="golden-device-lightkit-20241219-latest"

# Other components (MQTT, drivers, etc.) remain unchanged
```

### Cross-Environment LightKit Deployment

```bash
# Backup LightKit from staging golden device
ansible-playbook tulip.edge.backup_lightkit --limit staging-golden-device

# Test deployment to staging devices
ansible-playbook tulip.edge.restore_lightkit \
  --limit staging_devices \
  -e lightkit_backup_name="staging-golden-device-lightkit-20241219-100000"

# After validation, deploy to production
ansible-playbook tulip.edge.restore_lightkit \
  --limit production_devices \
  -e lightkit_backup_name="staging-golden-device-lightkit-20241219-100000"
```

### LightKit Disaster Recovery

```bash
# Replace failed device's LightKit configuration
ansible-playbook tulip.edge.restore_lightkit \
  --limit replacement-device \
  -e lightkit_backup_name="failed-device-lightkit-20241218-last-good"
```

## Integration with Provisioning Workflows

### Extended Golden Device Provisioning Playbook

```yaml
# golden_device_provision_with_lightkit.yml
---
- name: Provision Devices from Golden Device (including LightKit)
  hosts: "{{ target_group | default('newly_provisioned') }}"
  vars:
    golden_device: "{{ golden_device | default('golden-device') }}"
    backup_date: "{{ backup_date | default('latest') }}"
  tasks:
    - name: Login to target devices
      ansible.builtin.import_playbook: tulip.edge.login

    - name: Deploy MQTT Broker from golden device
      ansible.builtin.import_playbook: tulip.edge.restore_mqtt_broker
      vars:
        mqtt_broker_backup_name: "{{ golden_device }}-mqtt-broker-{{ backup_date }}"

    - name: Deploy MQTT Bridge from golden device
      ansible.builtin.import_playbook: tulip.edge.restore_mqtt_bridge
      vars:
        mqtt_bridge_backup_name: "{{ golden_device }}-mqtt-bridge-{{ backup_date }}"

    - name: Deploy Drivers from golden device
      ansible.builtin.import_playbook: tulip.edge.restore_drivers
      vars:
        drivers_backup_name: "{{ golden_device }}-drivers-{{ backup_date }}"

    - name: Deploy Root Certificates from golden device
      ansible.builtin.import_playbook: tulip.edge.restore_root_certs
      vars:
        root_certs_backup_name: "{{ golden_device }}-root-certs-{{ backup_date }}"

    - name: Deploy LightKit from golden device
      ansible.builtin.import_playbook: tulip.edge.restore_lightkit
      vars:
        lightkit_backup_name: "{{ golden_device }}-lightkit-{{ backup_date }}"
      when: deploy_lightkit | default(true)

    - name: Authenticate with Tulip factory
      ansible.builtin.import_playbook: tulip.edge.gateway_tulip_auth

    - name: Verify deployment
      ansible.builtin.import_playbook: tulip.edge.gateway_device_info
```

Usage:
```bash
# Deploy everything including LightKit
ansible-playbook golden_device_provision_with_lightkit.yml \
  -e target_group=newly_provisioned \
  -e backup_date=20241219-certified

# Deploy without LightKit
ansible-playbook golden_device_provision_with_lightkit.yml \
  -e target_group=newly_provisioned \
  -e backup_date=20241219-certified \
  -e deploy_lightkit=false
```

## Variables and Configuration

### LightKit-specific Variables

- `lightkit_backup_name` - Specific backup to restore (without .json extension)
- `lightkit_backup_dir` - Directory for backup files (default: './backups')

### Example Inventory Configuration

```ini
[tulip_edge_devices]
golden-device ansible_host=172.16.15.130
device-001 ansible_host=172.16.15.140

[tulip_edge_devices:vars]
# Custom backup directory for all components including LightKit
lightkit_backup_dir=./backups/lightkit
mqtt_backup_dir=./backups/mqtt
drivers_backup_dir=./backups/drivers
```

## Troubleshooting

### Common LightKit Issues

**LightKit backup not found:**
```bash
# Check available LightKit backups
ls backups/device-name-lightkit-*.json

# Verify backup name format (without .json)
ansible-playbook tulip.edge.restore_lightkit \
  --limit device-name \
  -e lightkit_backup_name="device-lightkit-20241219-143022" \
  -vv
```

**LightKit restore failures:**
```bash
# Check backup file content
cat backups/device-lightkit-backup.json | jq '.' | head -20

# Run restore with verbose output
ansible-playbook tulip.edge.restore_lightkit \
  --limit device-name \
  -e lightkit_backup_name="backup-name" \
  -vv
```

## Best Practices

1. **Include LightKit in Regular Backups**: Add LightKit to your regular golden device backup procedures
2. **Test LightKit Deployments**: Always test LightKit configurations in staging before production
3. **Version LightKit Backups**: Use consistent naming for important LightKit configuration versions
4. **Monitor LightKit Health**: Include LightKit status in your device health monitoring
5. **Component Coordination**: Consider dependencies between LightKit and other components when doing selective deployments

LightKit backup and restore functionality follows the same patterns as other Tulip Edge components, making it easy to integrate into existing provisioning workflows.
