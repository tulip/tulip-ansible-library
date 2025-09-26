# Tulip Edge Ansible Collection

An Ansible collection for managing Tulip Edge devices with comprehensive gateway authentication and provisioning capabilities.

## Installation

### From Ansible Galaxy (once published)
```bash
ansible-galaxy collection install tulip.edge
```

### From GitHub (development)
```bash
ansible-galaxy collection install git+https://github.com/your-org/tulip-ansible.git#/collections/ansible_collections/tulip/edge
```

### From Local Source
```bash
git clone https://github.com/your-org/tulip-ansible.git
cd tulip-ansible
ansible-galaxy collection install ./collections/ansible_collections/tulip/edge
```

## Overview

The Tulip Edge collection provides:
- **Gateway Authentication**: Authenticate devices with Tulip factory instances
- **Golden Device Provisioning**: Copy configurations from reference devices to new devices
- **Backup & Restore**: Component-level configuration management
- **Device Registration**: Integration with external registration systems
- **Verification & Monitoring**: Built-in health checks and validation

## Quick Start

### 1. Configure Inventory

```ini
[tulip_edge_devices]
golden-device ansible_host=172.16.15.130
new-device-001 ansible_host=172.16.15.140

[golden_devices]
golden-device

[newly_provisioned]  
new-device-001

[tulip_edge_devices:vars]
tulip_factory_url=https://your-factory.tulip.co
tulip_admin_email=admin@yourcompany.com
tulip_admin_password_sha256=your_sha256_hash
tulip_client_name=YourCompanyName
```

### 2. Basic Golden Device Provisioning

```bash
# Backup golden device
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device

# Deploy to new devices
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit newly_provisioned \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-143022"

# Authenticate with factory
ansible-playbook tulip.edge.gateway_tulip_auth --limit newly_provisioned
```

## Available Playbooks

- `tulip.edge.login` - Authenticate with devices
- `tulip.edge.backup_mqtt_broker` - Backup MQTT broker configuration
- `tulip.edge.backup_mqtt_bridge` - Backup MQTT bridge configuration  
- `tulip.edge.backup_drivers` - Backup device drivers
- `tulip.edge.backup_root_certs` - Backup root certificates
- `tulip.edge.backup_lightkit` - Backup LightKit configuration
- `tulip.edge.restore_mqtt_broker` - Restore MQTT broker configuration
- `tulip.edge.restore_mqtt_bridge` - Restore MQTT bridge configuration
- `tulip.edge.restore_drivers` - Restore device drivers
- `tulip.edge.restore_root_certs` - Restore root certificates
- `tulip.edge.restore_lightkit` - Restore LightKit configuration
- `tulip.edge.gateway_tulip_auth` - Authenticate with Tulip factory
- `tulip.edge.gateway_device_info` - Get device information
- `tulip.edge.gateway_check_internet` - Check internet connectivity
- `tulip.edge.gateway_serial_number` - Get device serial number
- `tulip.edge.register` - Register devices with external systems

## Documentation

- [Provisioning Guide](docs/PROVISIONING.md) - Complete golden device provisioning workflow
- [Integration Guide](docs/INTEGRATION_GUIDE.md) - CI/CD and workflow integration examples

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: https://github.com/your-org/tulip-ansible/issues  
- **Documentation**: https://github.com/your-org/tulip-ansible
- **Homepage**: https://tulip.co
