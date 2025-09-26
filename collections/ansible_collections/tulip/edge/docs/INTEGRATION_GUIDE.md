# Tulip Edge Integration Guide

This guide shows how to integrate Tulip Edge collection capabilities into your existing Ansible workflows.

## Installation

Install the Tulip Edge collection from Ansible Galaxy:

```bash
ansible-galaxy collection install tulip.edge
```

## Quick Integration

### 1. Inventory Configuration

Add these variables to your existing inventory:

```ini
[your_device_group:vars]
# Factory Authentication
tulip_factory_url=https://your-factory.tulip.co
tulip_admin_email=admin@yourcompany.com
tulip_admin_password_sha256=your_sha256_hash

# Client Information  
tulip_client_name=YourCompanyName
tulip_client_version=1.0.0
tulip_client_description=Production Gateway
```

### 2. Password Hash Generation

Generate secure password hashes:
```bash
echo -n "your_password" | sha256sum | cut -d' ' -f1
```

### 3. Core Playbook Integration

Add these playbooks to your existing workflows:

```yaml
# In your existing playbook
- import_playbook: tulip.edge.gateway_tulip_auth
  when: authenticate_with_factory | default(true)

- import_playbook: tulip.edge.register
  when: register_devices | default(false)
```

## Common Integration Patterns

### Device Provisioning Workflow

Integrate backup/restore into your device deployment process:

```yaml
# your_deployment.yml
- name: Deploy Device Configurations
  hosts: target_devices
  tasks:
    - name: Login to devices
      import_playbook: tulip.edge.login

    - name: Restore MQTT Broker
      import_playbook: tulip.edge.restore_mqtt_broker
      vars:
        mqtt_broker_backup_name: "{{ reference_device }}-mqtt-broker-{{ backup_version }}"

    - name: Restore Drivers  
      import_playbook: tulip.edge.restore_drivers
      vars:
        drivers_backup_name: "{{ reference_device }}-drivers-{{ backup_version }}"

    - name: Authenticate with Factory
      import_playbook: tulip.edge.gateway_tulip_auth

    - name: Verify Deployment
      import_playbook: tulip.edge.gateway_device_info
```

### CI/CD Pipeline Integration

#### GitLab CI Example
```yaml
stages:
  - backup
  - deploy
  - verify

backup_golden_device:
  stage: backup
  script:
    - ansible-playbook tulip.edge.backup_mqtt_broker --limit golden_device
    - ansible-playbook tulip.edge.backup_drivers --limit golden_device

deploy_configurations:
  stage: deploy
  script:
    - ansible-playbook tulip.edge.restore_mqtt_broker --limit $TARGET_DEVICES -e mqtt_broker_backup_name=$BACKUP_NAME
    - ansible-playbook tulip.edge.gateway_tulip_auth --limit $TARGET_DEVICES

verify_deployment:
  stage: verify
  script:
    - ansible-playbook tulip.edge.gateway_device_info --limit $TARGET_DEVICES
    - ansible-playbook tulip.edge.gateway_check_internet --limit $TARGET_DEVICES
```

#### GitHub Actions Example
```yaml
name: Deploy Device Configurations
on:
  workflow_dispatch:
    inputs:
      target_devices:
        description: 'Target device group'
        required: true
      backup_version:
        description: 'Backup version to deploy'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy configurations
        run: |
          ansible-playbook tulip.edge.restore_mqtt_broker \
            --limit ${{ github.event.inputs.target_devices }} \
            -e mqtt_broker_backup_name=golden-device-mqtt-broker-${{ github.event.inputs.backup_version }}
      - name: Authenticate devices
        run: |
          ansible-playbook tulip.edge.gateway_tulip_auth \
            --limit ${{ github.event.inputs.target_devices }}
```

### Disaster Recovery Integration

Add to your existing disaster recovery procedures:

```yaml
# disaster_recovery.yml
- name: Emergency Device Replacement
  hosts: replacement_devices
  vars:
    failed_device: "{{ hostvars[inventory_hostname]['failed_device'] }}"
    backup_timestamp: "{{ hostvars[inventory_hostname]['backup_timestamp'] | default('latest') }}"
  tasks:
    - name: Restore from last known good backup
      import_playbook: tulip.edge.restore_mqtt_broker
      vars:
        mqtt_broker_backup_name: "{{ failed_device }}-mqtt-broker-{{ backup_timestamp }}"
    
    - name: Re-authenticate with factory
      import_playbook: tulip.edge.gateway_tulip_auth
```

## Ansible Tower/AWX Integration

### Job Templates

Create reusable job templates:

**Template: "Authenticate Tulip Gateways"**
- Playbook: `gateway_tulip_auth.yml`
- Inventory: Your device inventory
- Variables: Factory credentials
- Survey: Device group selection

**Template: "Deploy Device Configuration"**
- Playbook: Your deployment playbook
- Variables: 
  - `backup_name`: Text field for backup selection
  - `target_group`: Multiple choice for device groups
- Survey enabled for runtime input

**Template: "Provision New Devices"**
- Playbook: Combined provisioning workflow
- Variables:
  - `reference_device`: Device to backup from
  - `target_devices`: Devices to provision
- Chained with authentication template

### Workflow Templates

Chain templates together:
1. Backup Golden Device → 2. Deploy Configuration → 3. Authenticate Devices → 4. Verify Deployment

## Makefile Integration

Add to your existing Makefile:

```makefile
# Tulip Edge Operations
.PHONY: tulip-auth tulip-provision tulip-backup tulip-restore

tulip-auth:
	ansible-playbook gateway_tulip_auth.yml --limit $(DEVICES)

tulip-backup:
	ansible-playbook backup_mqtt_broker.yml --limit $(SOURCE_DEVICE)
	ansible-playbook backup_drivers.yml --limit $(SOURCE_DEVICE)

tulip-provision:
	$(MAKE) tulip-backup SOURCE_DEVICE=$(REFERENCE_DEVICE)
	ansible-playbook restore_mqtt_broker.yml --limit $(TARGET_DEVICES) -e mqtt_broker_backup_name=$(BACKUP_NAME)
	$(MAKE) tulip-auth DEVICES=$(TARGET_DEVICES)

# Usage examples:
# make tulip-auth DEVICES=production_floor
# make tulip-provision REFERENCE_DEVICE=golden_device TARGET_DEVICES=new_devices BACKUP_NAME=golden-device-mqtt-broker-20241219
```

## Ansible Vault Integration

Secure credential management:

```ini
# inventory/group_vars/all/vault.yml (encrypted)
$ANSIBLE_VAULT;1.1;AES256
vault_tulip_admin_password_sha256: your_encrypted_hash
vault_tulip_factory_url: your_encrypted_url

# inventory/group_vars/all/vars.yml (plaintext)
tulip_admin_password_sha256: "{{ vault_tulip_admin_password_sha256 }}"
tulip_factory_url: "{{ vault_tulip_factory_url }}"
```

## Testing Integration

Add to your testing workflows:

```yaml
# test_playbook.yml
- name: Test Tulip Gateway Authentication
  hosts: test_devices
  tasks:
    - name: Authenticate test device
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_tulip_auth.yml
      
    - name: Verify authentication worked
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_device_info.yml
      
    - name: Check connectivity
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_check_internet.yml
```

## Monitoring Integration

Add health checks to your monitoring:

```yaml
# monitoring_playbook.yml
- name: Tulip Device Health Check
  hosts: tulip_devices
  tasks:
    - name: Check device status
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_device_info.yml
      
    - name: Verify internet connectivity
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_check_internet.yml
      
    - name: Re-authenticate if needed
      import_playbook: collections/ansible_collections/tulip/edge/playbooks/gateway_tulip_auth.yml
      when: device_authentication_expired | default(false)
```

## Best Practices for Integration

### 1. Variable Management
- Use group_vars for common settings
- Use host_vars for device-specific overrides
- Store sensitive data in Ansible Vault

### 2. Error Handling
```yaml
- name: Authenticate with factory
  import_playbook: gateway_tulip_auth.yml
  ignore_errors: true
  register: auth_result
  
- name: Handle authentication failure
  debug:
    msg: "Authentication failed, check credentials"
  when: auth_result.failed | default(false)
```

### 3. Backup Management
- Use consistent backup naming: `device-component-timestamp`
- Store backup names in variables for reuse
- Implement backup retention policies

### 4. Idempotency
All playbooks are idempotent - safe to run multiple times. Use `--check` mode for dry runs:
```bash
ansible-playbook gateway_tulip_auth.yml --limit test_device --check
```

## Migration from Existing Systems

### Gradual Integration
1. Start with authentication on test devices
2. Add backup/restore for non-critical components
3. Expand to full provisioning workflows
4. Integrate with existing CI/CD pipelines

### Validation Steps
1. Test authentication with a single device
2. Verify backup/restore with test configurations
3. Run full provisioning workflow on test devices
4. Monitor and validate before production rollout

This integration approach allows you to adopt Tulip Edge capabilities incrementally within your existing infrastructure and workflows.
