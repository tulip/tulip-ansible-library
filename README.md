# Tulip Edge Ansible Collection

An Ansible collection for managing Tulip Edge devices with comprehensive gateway authentication and provisioning capabilities.

## Installation

### From GitHub (Recommended for Development)
```bash
ansible-galaxy collection install git+https://github.com/your-org/tulip-ansible.git#/collections/ansible_collections/tulip/edge
```

### From Ansible Galaxy (Once Published)
```bash
ansible-galaxy collection install tulip.edge
```

### From Local Build
```bash
git clone https://github.com/your-org/tulip-ansible.git
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
ansible-playbook tulip.edge.backup_mqtt_broker --limit golden-device

# Deploy to new devices  
ansible-playbook tulip.edge.restore_mqtt_broker \
  --limit new-device-001 \
  -e mqtt_broker_backup_name="golden-device-mqtt-broker-20241219-143022"

# Authenticate with Tulip factory
ansible-playbook tulip.edge.gateway_tulip_auth --limit new-device-001
```

## Documentation

- **[Provisioning Guide](collections/ansible_collections/tulip/edge/docs/PROVISIONING.md)** - Complete golden device provisioning workflow
- **[Integration Guide](collections/ansible_collections/tulip/edge/docs/INTEGRATION_GUIDE.md)** - CI/CD and workflow integration examples

## Available Playbooks

The collection provides the following playbooks:

### Core Operations
- `tulip.edge.login` - Authenticate with devices
- `tulip.edge.gateway_tulip_auth` - Authenticate with Tulip factory
- `tulip.edge.gateway_device_info` - Get device information
- `tulip.edge.gateway_check_internet` - Check internet connectivity
- `tulip.edge.register` - Register devices with external systems

### Backup & Restore
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

### Configuration Management
- `tulip.edge.configure_network` - Configure network settings
- `tulip.edge.configure_ntp` - Configure NTP settings
- `tulip.edge.configure_https` - Configure HTTPS settings
- `tulip.edge.configure_http_proxy` - Configure HTTP proxy

### Node-RED Management
- `tulip.edge.backup_nodered` - Backup Node-RED flows
- `tulip.edge.restore_nodered` - Restore Node-RED flows
- `tulip.edge.enable_nodered` - Enable Node-RED service
- `tulip.edge.disable_nodered` - Disable Node-RED service

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

MIT License - see [LICENSE](collections/ansible_collections/tulip/edge/LICENSE) for details.

## Support

- **Issues**: https://github.com/your-org/tulip-ansible/issues
- **Documentation**: https://github.com/your-org/tulip-ansible/tree/main/collections/ansible_collections/tulip/edge/docs
- **Homepage**: https://tulip.co
