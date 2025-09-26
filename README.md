# Tulip Edge Ansible Collection

An Ansible collection for managing Tulip Edge devices with comprehensive gateway authentication and provisioning capabilities.

## Installation

### From GitHub (Recommended for Development)
```bash
ansible-galaxy collection install git+https://github.com/tulip/tulip-ansible-library.git#/collections/ansible_collections/tulip/edge
```

### From Ansible Galaxy (Once Published)
```bash
ansible-galaxy collection install tulip.edge
```

### From Local Build
```bash
git clone https://github.com/tulip/tulip-ansible-library.git
cd tulip-ansible/collections/ansible_collections/tulip/edge
ansible-galaxy collection build
ansible-galaxy collection install tulip-edge-*.tar.gz
```

## Quick Start

### 1. Configure Your Inventory
```ini
[tulip_edge_devices]
golden-device ansible_host=172.16.15.130
new-device-001 ansible_host=172.16.15.140

[tulip_edge_devices:vars]
tulip_factory_url=https://your-factory.tulip.co
tulip_admin_email=admin@yourcompany.com
tulip_admin_password_sha256=your_sha256_hash
tulip_client_name=YourCompanyName
```

### 2. Golden Device Provisioning
```bash
# Backup golden device configuration
ansible-playbook tulip.edge.v0_backup_mqtt_broker --limit golden-device

# Deploy to new devices  
ansible-playbook tulip.edge.v0_restore_mqtt_broker \
  --limit new-device-001 \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-143022"

# Authenticate with Tulip factory
ansible-playbook tulip.edge.v0_gateway_tulip_auth --limit new-device-001
```

## Documentation

- **[Provisioning Guide](collections/ansible_collections/tulip/edge/docs/PROVISIONING.md)** - Complete golden device provisioning workflow
- **[Integration Guide](collections/ansible_collections/tulip/edge/docs/INTEGRATION_GUIDE.md)** - CI/CD and workflow integration examples

## Available Playbooks

### Authentication & Device Management
- `tulip.edge.login` - Authenticate with devices
- `tulip.edge.check_login` - Check authentication status
- `tulip.edge.check_and_refresh_login` - Check and refresh authentication
- `tulip.edge.change_password` - Change device password
- `tulip.edge.register` - Register devices with external systems
- `tulip.edge.factory_reset` - Perform factory reset on devices

### Backup & Restore - Network Components
- `tulip.edge.backup_mqtt_broker` - Backup MQTT broker configuration
- `tulip.edge.restore_mqtt_broker` - Restore MQTT broker configuration
- `tulip.edge.backup_mqtt_bridge` - Backup MQTT bridge configuration  
- `tulip.edge.restore_mqtt_bridge` - Restore MQTT bridge configuration
- `tulip.edge.backup_ntp` - Backup NTP configuration
- `tulip.edge.restore_ntp` - Restore NTP configuration
- `tulip.edge.backup_http_proxy` - Backup HTTP proxy configuration
- `tulip.edge.restore_http_proxy` - Restore HTTP proxy configuration
- `tulip.edge.backup_network_certificates` - Backup network certificates
- `tulip.edge.restore_network_certificates` - Restore network certificates

### Backup & Restore - Security & System
- `tulip.edge.backup_https` - Backup HTTPS configuration
- `tulip.edge.restore_https` - Restore HTTPS configuration
- `tulip.edge.backup_root_certs` - Backup root certificates
- `tulip.edge.restore_root_certs` - Restore root certificates
- `tulip.edge.backup_drivers` - Backup device drivers
- `tulip.edge.restore_drivers` - Restore device drivers

### Backup & Restore - Applications
- `tulip.edge.backup_lightkit` - Backup LightKit configuration
- `tulip.edge.restore_lightkit` - Restore LightKit configuration
- `tulip.edge.backup_nodered` - Backup Node-RED configuration
- `tulip.edge.restore_nodered` - Restore Node-RED configuration

### Service Management
- `tulip.edge.enable_mqtt_broker` - Enable MQTT broker service
- `tulip.edge.disable_mqtt_broker` - Disable MQTT broker service
- `tulip.edge.enable_nodered` - Enable Node-RED service
- `tulip.edge.disable_nodered` - Disable Node-RED service
- `tulip.edge.upgrade_nodered` - Upgrade Node-RED version
- `tulip.edge.rollback_nodered` - Rollback Node-RED version

### Configuration Management
- `tulip.edge.configure_network` - Configure network settings
- `tulip.edge.configure_ntp` - Configure NTP settings
- `tulip.edge.configure_http_proxy` - Configure HTTP proxy settings
- `tulip.edge.configure_https` - Configure HTTPS settings
- `tulip.edge.toggle_http_proxy` - Toggle HTTP proxy on/off
- `tulip.edge.toggle_https` - Toggle HTTPS on/off
- `tulip.edge.toggle_mqtt_bridge` - Toggle MQTT bridge on/off

### Gateway Information & Diagnostics
- `tulip.edge.gateway_tulip_auth` - Authenticate with Tulip factory
- `tulip.edge.gateway_device_info` - Get device information
- `tulip.edge.gateway_check_internet` - Check internet connectivity
- `tulip.edge.gateway_serial_number` - Get device serial number
- `tulip.edge.gateway_tulip_url` - Get/check Tulip factory URL
- `tulip.edge.gateway_locate` - Physically locate device (LED flash)
- `tulip.edge.gateway_network_health_check` - Perform network diagnostics
## Repository Structure

```
tulip-ansible/
├── collections/ansible_collections/tulip/edge/    # Main collection
│   ├── galaxy.yml                                 # Collection metadata
│   ├── README.md                                  # Collection README
│   ├── LICENSE                                    # License file
│   ├── playbooks/                                 # All playbooks
│   ├── roles/                                     # Ansible roles
│   └── docs/                                      # Documentation
├── examples/                                      # Example configurations
├── docs/                                          # Main documentation
└── README.md                                      # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `ansible-galaxy collection build`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE.MD) for details.
