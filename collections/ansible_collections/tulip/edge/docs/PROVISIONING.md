# Tulip Edge Device Provisioning Guide

This guide covers using the Tulip Edge Ansible collection to provision new devices by copying configurations from a reference "golden" device.

## Installation

Install the Tulip Edge collection from Ansible Galaxy:

```bash
ansible-galaxy collection install tulip.edge
```

## Overview

The golden device provisioning workflow allows you to:
1. **Select a Golden Device**: Choose a properly configured reference device
2. **Backup Golden Configuration**: Capture all component configurations
3. **Deploy to New Devices**: Apply golden device settings to new/replacement devices
4. **Authenticate & Verify**: Register devices and validate deployment

## Quick Start

### 1. Inventory Configuration

Configure your inventory with the golden device and target devices:

```ini
[tulip_edge_devices]
golden-device ansible_host=172.16.15.130
new-device-001 ansible_host=172.16.15.140
new-device-002 ansible_host=172.16.15.141
replacement-device ansible_host=172.16.15.150

[golden_devices]
golden-device

[newly_provisioned]
new-device-001
new-device-002
replacement-device

[tulip_edge_devices:vars]
# Factory Authentication
tulip_factory_url=https://your-factory.tulip.co
tulip_admin_email=admin@yourcompany.com
tulip_admin_password_sha256=your_sha256_hash

# Client Information
tulip_client_name=YourCompanyName
tulip_client_version=1.0.0
tulip_client_description=Production Gateway
```

### 2. Generate Password Hash

Create SHA256 hash for secure password storage:
```bash
echo -n "your_password" | sha256sum | cut -d' ' -f1
```

### 3. Basic Golden Device Provisioning

```bash
# 1. Login to golden device
ansible-playbook tulip.edge.login --limit golden-device

# 2. Backup golden device configurations
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
ansible-playbook tulip.edge.backup_mqtt_bridge --limit golden-device
ansible-playbook tulip.edge.backup_drivers --limit golden-device
ansible-playbook tulip.edge.backup_root_certs --limit golden-device
ansible-playbook tulip.edge.backup_lightkit --limit golden-device

# 3. Login to target devices
ansible-playbook tulip.edge.login --limit newly_provisioned

# 4. Deploy golden configurations to target devices
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

# 5. Authenticate with factory
ansible-playbook tulip.edge.gateway_tulip_auth --limit newly_provisioned

# 6. Register with external systems (optional)
ansible-playbook tulip.edge.register --limit newly_provisioned

# 7. Verify deployment
ansible-playbook tulip.edge.gateway_device_info --limit newly_provisioned
ansible-playbook tulip.edge.gateway_check_internet --limit newly_provisioned
```

## Golden Device Management

### Selecting Your Golden Device

Choose a device that represents your ideal configuration:
- **Fully Configured**: All MQTT brokers, bridges, and drivers properly set up
- **Tested & Validated**: Known working configuration in your environment
- **Up-to-Date**: Latest firmware and configuration standards
- **Representative**: Matches the configuration needed for your fleet

### Creating Golden Device Backups

#### List Available Backups
```bash
# List all backups
ls -la backups/

# List backups for golden device
ls -la backups/ | grep golden-device

# Get latest backup for each component
ls -t backups/golden-device-mqtt-broker-*.json | head -1
ls -t backups/golden-device-mqtt-bridge-*.json | head -1
ls -t backups/golden-device-drivers-*.json | head -1
ls -t backups/golden-device-root-certs-*.json | head -1
ls -t backups/golden-device-lightkit-*.json | head -1
```

#### Backup All Golden Device Components
```bash
# Comprehensive golden device backup
ansible-playbook tulip.edge.login --limit golden-device

ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
ansible-playbook tulip.edge.backup_mqtt_bridge --limit golden-device  
ansible-playbook tulip.edge.backup_drivers --limit golden-device
ansible-playbook tulip.edge.backup_root_certs --limit golden-device
ansible-playbook tulip.edge.backup_lightkit --limit golden-device

echo "Golden device backup completed at $(date)"
ls -la backups/golden-device-*
```

## Provisioning Workflows

### Complete Device Provisioning

Deploy your golden device configuration to provision new devices:

```yaml
# golden_device_provision.yml
---
- name: Provision Devices from Golden Device
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

    - name: Authenticate with Tulip factory
      ansible.builtin.import_playbook: tulip.edge.gateway_tulip_auth

    - name: Register devices (optional)
      ansible.builtin.import_playbook: tulip.edge.register
      when: register_devices | default(false)

    - name: Verify deployment
      ansible.builtin.import_playbook: tulip.edge.gateway_device_info
```

Usage:
```bash
# Provision using latest golden device backups
ansible-playbook golden_device_provision.yml

# Provision specific devices with specific backup date
ansible-playbook golden_device_provision.yml \
  -e target_group=production_floor \
  -e golden_device=prod-golden-device \
  -e backup_date=20241219-certified
```

### Disaster Recovery from Golden Device

Quickly replace a failed device using golden device configuration:

```yaml
# disaster_recovery.yml
---
- name: Emergency Device Replacement using Golden Device
  hosts: "{{ replacement_devices }}"
  vars:
    golden_device: "{{ golden_device | default('golden-device') }}"
    backup_version: "{{ backup_version | default('latest-stable') }}"
  tasks:
    - name: Deploy golden device MQTT configuration
      ansible.builtin.import_playbook: tulip.edge.restore_mqtt_broker
      vars:
        mqtt_broker_backup_name: "{{ golden_device }}-mqtt-broker-{{ backup_version }}"

    - name: Deploy golden device drivers
      ansible.builtin.import_playbook: tulip.edge.restore_drivers
      vars:
        drivers_backup_name: "{{ golden_device }}-drivers-{{ backup_version }}"

    - name: Authenticate replacement device
      ansible.builtin.import_playbook: tulip.edge.gateway_tulip_auth
```

Usage:
```bash
ansible-playbook disaster_recovery.yml \
  -e replacement_devices=replacement-device-001 \
  -e golden_device=prod-golden-device \
  -e backup_version=20241218-stable
```

## Working with Golden Device Backups

### Backup Versioning Strategy

Use consistent naming for golden device backup versions:

```bash
# Create timestamped golden backups
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
# Results in: golden-device-mqtt-broker-20241219-143022.json

# Create named versions for important milestones
# Manually rename: golden-device-mqtt-broker-20241219-143022.json → golden-device-mqtt-broker-v1.0-stable.json

# Deploy named version
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit production_devices \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-v1.0-stable"
```

### Multiple Golden Devices

Manage different golden devices for different environments:

```ini
[golden_devices]
prod-golden-device ansible_host=172.16.10.100
staging-golden-device ansible_host=172.16.20.100
dev-golden-device ansible_host=172.16.30.100

[production_devices]
prod-device-001 ansible_host=172.16.10.101
prod-device-002 ansible_host=172.16.10.102

[staging_devices]  
staging-device-001 ansible_host=172.16.20.101
staging-device-002 ansible_host=172.16.20.102
```

```bash
# Backup production golden device
ansible-playbook tulip.edge.backup_mqtt_broker --limit prod-golden-device

# Deploy production golden config to staging for testing
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit staging_devices \
  -e mqtt_broker_backup_name="prod-golden-device-mqtt-broker-20241219-100000"

# After validation, deploy to production
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit production_devices \
  -e mqtt_broker_backup_name="prod-golden-device-mqtt-broker-20241219-100000"
```

### Golden Device Configuration Updates

Update your golden device and propagate changes:

```bash
# 1. Update golden device configuration manually or via automation

# 2. Create new backup of updated golden device
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
ansible-playbook tulip.edge.backup_drivers --limit golden-device

# 3. Test deployment on staging devices first
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit staging_devices \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-154500"

# 4. After validation, deploy to production fleet
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit production_devices \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-154500"
```

## Advanced Golden Device Scenarios

### Selective Component Deployment

Deploy only specific components from your golden device:

```bash
# Update only MQTT broker from golden device, keep existing drivers
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit target_devices \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-latest"

# Drivers remain unchanged on target devices
```

### Cross-Environment Golden Device Promotion

Promote configurations between environments:

```bash
# 1. Backup staging golden device (tested configuration)
ansible-playbook tulip.edge.backup_mqtt_broker --limit staging-golden-device

# 2. Deploy staging golden config to production golden device
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit prod-golden-device \
  -e mqtt_broker_backup_name="staging-golden-device-mqtt-broker-20241219-validated"

# 3. Create new production golden backup
ansible-playbook tulip.edge.backup_mqtt_broker --limit prod-golden-device

# 4. Deploy to production fleet
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit production_devices \
  -e mqtt_broker_backup_name="prod-golden-device-mqtt-broker-20241219-160000"
```

### Golden Device Health Monitoring

Monitor your golden device to ensure it remains the source of truth:

```yaml
# golden_device_health.yml
---
- name: Golden Device Health Check
  hosts: golden_devices
  tasks:
    - name: Check golden device status
      ansible.builtin.import_playbook: tulip.edge.gateway_device_info
      
    - name: Verify internet connectivity
      ansible.builtin.import_playbook: tulip.edge.gateway_check_internet
      
    - name: Create backup if healthy
      ansible.builtin.import_playbook: tulip.edge.backup_mqtt_broker
      when: device_health_ok | default(true)
```

## Security Best Practices

### Golden Device Access Control

Protect your golden device:

```ini
[golden_devices:vars]
# Restrict golden device access
ansible_user=golden_admin
ansible_become=true

# Separate credentials for golden devices
tulip_admin_email=golden-admin@yourcompany.com
tulip_admin_password_sha256=different_hash_for_golden_device
```

### Backup Security

Secure your golden device backups:

```bash
# Use Ansible Vault for sensitive golden device credentials
ansible-vault create group_vars/golden_devices/vault.yml

# Store golden device backups in version control
git add backups/golden-device-*
git commit -m "Golden device backup - $(date)"

# Set proper backup file permissions
chmod 600 backups/golden-device-*.json
```

## Automation Integration

### Scheduled Golden Device Backups

```yaml
# .github/workflows/golden-device-backup.yml
name: Golden Device Backup
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Create golden device backup
        run: |
          ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device
          ansible-playbook tulip.edge.backup_drivers --limit golden-device
      - name: Commit backups
        run: |
          git add backups/
          git commit -m "Automated golden device backup - $(date)"
          git push
```

### CI/CD Golden Device Deployment

```yaml
# .gitlab-ci.yml
stages:
  - backup-golden
  - deploy-staging
  - deploy-production

backup-golden-device:
  stage: backup-golden
  script:
    - ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device

deploy-to-staging:
  stage: deploy-staging
  script:
    - ansible-playbook tulip.edge.restore_mqtt_broker --limit staging_devices -e mqtt_broker_backup_name=$GOLDEN_BACKUP_NAME
    - ansible-playbook tulip.edge.gateway_tulip_auth --limit staging_devices

deploy-to-production:
  stage: deploy-production
  script:
    - ansible-playbook tulip.edge.restore_mqtt_broker --limit production_devices -e mqtt_broker_backup_name=$GOLDEN_BACKUP_NAME
    - ansible-playbook tulip.edge.gateway_tulip_auth --limit production_devices
  when: manual
  only:
    - main
```

## Troubleshooting

### Common Golden Device Issues

**Golden device unreachable:**
```bash
# Test connectivity to golden device
ansible golden-device -m ping

# Check golden device status
ansible-playbook tulip.edge.gateway_device_info --limit golden-device
```

**Backup deployment failures:**
```bash
# Verify backup file exists
ls backups/golden-device-mqtt-broker-*.json

# Use correct backup name format (without .json)
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit target-device \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-143022" \
  -vv
```

**Golden device authentication issues:**
```bash
# Re-authenticate golden device
ansible-playbook tulip.edge.login --limit golden-device

# Verify golden device credentials in inventory
ansible-inventory --host golden-device
```

## Best Practices

1. **Golden Device Maintenance**: Keep your golden device updated and well-maintained
2. **Regular Backups**: Create regular backups of your golden device configuration
3. **Version Control**: Store golden device backups in version control with meaningful names
4. **Testing Pipeline**: Always test golden device configurations in staging before production
5. **Documentation**: Document your golden device configuration standards and procedures
6. **Access Control**: Limit access to golden devices and use separate credentials
7. **Monitoring**: Monitor golden device health and backup creation processes

This golden device approach ensures consistent, reliable provisioning of your Tulip Edge device fleet while maintaining full traceability and control over your configuration standards.
