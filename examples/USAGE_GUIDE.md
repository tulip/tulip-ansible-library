# Tulip Edge API Management Guide

This guide shows how to use the Tulip Edge collection to manage fleets of edge devices via their HTTP APIs.

## Quick Start

1. **Install the collection:**
   ```bash
   ansible-galaxy collection install tulip.edge
   ```

2. **Set up your inventory:** (see `examples/inventory.ini`)
   ```ini
   [tulip_edge_devices]
   edge-001 ansible_host=192.168.1.101
   edge-002 ansible_host=192.168.1.102
   
   [tulip_edge_devices:vars]
   device_password="{{ vault_edge_password }}"
   ```

3. **Create an Ansible Vault for sensitive data:**
   ```bash
   ansible-vault create group_vars/all/vault.yml
   ```
   Add your password:
   ```yaml
   vault_edge_password: your_device_password_here
   ```

## Basic Operations

### Authentication

All operations except `register` and `login` require authentication. Always start with login:

```bash
# Login to all devices (stores tokens for subsequent operations)
ansible-playbook tulip.edge.login -i inventory.ini --ask-vault-pass
```

### Device Registration

For new devices that need initial setup:

```bash
ansible-playbook tulip.edge.register -i inventory.ini --ask-vault-pass
```

## Fleet Operations

### Parallel Execution

All playbooks use `strategy: free` for maximum parallelism. You can control concurrency:

```bash
# Run on all devices in parallel
ansible-playbook tulip.edge.backup_nodered -i inventory.ini

# Limit parallelism to 5 devices at once  
ansible-playbook tulip.edge.backup_nodered -i inventory.ini --forks 5

# Run on specific groups
ansible-playbook tulip.edge.toggle_nodered -i inventory.ini --limit production_floor
```

## Available Operations

### Node-RED Management
```bash
# Enable/disable Node-RED
ansible-playbook tulip.edge.toggle_nodered -i inventory.ini -e nodered_state=true

# Backup Node-RED configuration
ansible-playbook tulip.edge.backup_nodered -i inventory.ini -e nodered_backup_name=prod-backup-$(date +%Y%m%d)

# Restore from backup
ansible-playbook tulip.edge.restore_nodered -i inventory.ini -e nodered_backup_name=prod-backup-20240115

# Upgrade Node-RED
ansible-playbook tulip.edge.upgrade_nodered -i inventory.ini

# Rollback Node-RED
ansible-playbook tulip.edge.rollback_nodered -i inventory.ini
```

### MQTT Management
```bash
# Toggle MQTT broker
ansible-playbook tulip.edge.toggle_mqtt_broker -i inventory.ini -e mqtt_broker_enabled=true

# Backup MQTT configuration
ansible-playbook tulip.edge.backup_mqtt_broker -i inventory.ini -e mqtt_backup_name=mqtt-config-backup

# Toggle MQTT bridge
ansible-playbook tulip.edge.toggle_mqtt_bridge -i inventory.ini -e mqtt_bridge_enabled=false
```

### Network Configuration
```bash
# Configure network settings (requires network_config variable)
ansible-playbook tulip.edge.configure_network -i inventory.ini -e @examples/example_vars.yml

# Configure NTP
ansible-playbook tulip.edge.configure_ntp -i inventory.ini -e @examples/example_vars.yml
```

### Security Operations
```bash
# Toggle HTTPS
ansible-playbook tulip.edge.toggle_https -i inventory.ini -e https_enabled=true

# Configure HTTPS with certificates
ansible-playbook tulip.edge.configure_https -i inventory.ini -e @examples/example_vars.yml

# Change device passwords
ansible-playbook tulip.edge.change_password -i inventory.ini -e new_password=new_secure_password

# Backup/restore certificates
ansible-playbook tulip.edge.backup_root_certs -i inventory.ini -e certs_backup_name=certs-backup-$(date +%Y%m%d)
```

### Proxy Configuration
```bash
# Toggle HTTP proxy
ansible-playbook tulip.edge.toggle_http_proxy -i inventory.ini -e http_proxy_enabled=true

# Configure proxy settings
ansible-playbook tulip.edge.configure_http_proxy -i inventory.ini -e @examples/example_vars.yml
```

### Driver Management
```bash
# Backup drivers
ansible-playbook tulip.edge.backup_drivers -i inventory.ini -e drivers_backup_name=drivers-v1.2.3

# Restore drivers
ansible-playbook tulip.edge.restore_drivers -i inventory.ini -e drivers_backup_name=drivers-v1.2.3
```

### System Operations
```bash
# Factory reset (DESTRUCTIVE - requires confirmation)
ansible-playbook tulip.edge.factory_reset -i inventory.ini -e confirm_reset=true
```

## Advanced Usage

### Using the Module Directly

You can also use the `tulip_edge_api` module directly in your own playbooks:

```yaml
- name: Custom device management
  hosts: tulip_edge_devices
  tasks:
    - name: Login to device
      tulip.edge.tulip_edge_api:
        host: "{{ inventory_hostname }}"
        action: login
        password: "{{ device_password }}"
      register: login_result
      
    - name: Custom Node-RED operation
      tulip.edge.tulip_edge_api:
        host: "{{ inventory_hostname }}"
        action: toggle_nodered
        token: "{{ login_result.token }}"
        parameters:
          enabled: true
          custom_param: value
```

### Error Handling and Retries

```yaml
- name: Robust fleet operation
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: backup_nodered
    token: "{{ tulip_auth_token }}"
    parameters:
      backup_name: "{{ backup_name }}"
  register: result
  retries: 3
  delay: 5
  until: result is succeeded
  ignore_errors: false
```

### Conditional Operations

```yaml
# Only backup on production devices
- name: Conditional backup
  include: tulip.edge.backup_nodered
  when: inventory_hostname in groups['production_floor']
```

## Monitoring and Logging

All operations return structured results. You can capture and process these:

```yaml
- name: Capture operation results
  tulip.edge.tulip_edge_api:
    host: "{{ inventory_hostname }}"
    action: toggle_nodered
    token: "{{ tulip_auth_token }}"
    parameters:
      enabled: true
  register: operation_result
  
- name: Log results
  lineinfile:
    path: /var/log/tulip-edge-operations.log
    line: "{{ ansible_date_time.iso8601 }} {{ inventory_hostname }} toggle_nodered {{ operation_result.result.status | default('unknown') }}"
  delegate_to: localhost
```

## Best Practices

1. **Always use Ansible Vault for passwords**
2. **Start with login playbook to authenticate all devices**
3. **Use `--limit` to test operations on a subset first**
4. **Backup before destructive operations**  
5. **Monitor operation results and implement retry logic**
6. **Use groups to organize devices by function/location**
7. **Test playbooks in a staging environment first**

## Troubleshooting

### Common Issues

1. **Authentication failures:** Check device passwords and network connectivity
2. **Timeout issues:** Increase `edge_api_timeout` or check network latency
3. **Parallel execution problems:** Reduce `--forks` or use `serial` to limit concurrency
4. **HTTPS certificate issues:** Ensure proper certificates are installed or disable SSL verification

### Debug Mode

Run playbooks with increased verbosity:
```bash
ansible-playbook tulip.edge.login -i inventory.ini -vvv
```
