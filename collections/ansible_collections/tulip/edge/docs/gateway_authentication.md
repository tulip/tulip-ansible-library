# Tulip Gateway Authentication Configuration

This document explains how to configure authentication parameters for Tulip Edge gateway devices in your Ansible inventory.

## Overview

The `gateway_tulip_auth.yml` playbook authenticates Tulip Edge devices with your Tulip factory instance. Authentication parameters are stored in the Ansible inventory file for security and maintainability.

## Configuration in Inventory File

### Basic Configuration

Add these parameters to your inventory file under `[tulip_edge_devices:vars]`:

```ini
[tulip_edge_devices:vars]
# Required: Tulip Factory Authentication Settings
tulip_factory_url=your-factory.mfg.tulip.co
tulip_admin_email=admin@yourcompany.com
tulip_admin_password_sha256=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

# Optional: Custom client info (JSON string)
tulip_client_info={"type":"gateway","name":"custom-name","hostname":"custom-host"}
```

### Generating Password Hash

For security, passwords are stored as SHA256 hashes. Use one of these methods:

**Method 1: Use the provided helper script**
```bash
./generate_password_hash.sh
```

**Method 2: Command line**
```bash
echo -n 'your_password' | sha256sum
```

**Method 3: Python**
```python
import hashlib
password = "your_password"
hash_value = hashlib.sha256(password.encode()).hexdigest()
print(hash_value)
```

### Advanced Configuration

#### Per-Location Configuration

Different device groups can use different Tulip instances:

```ini
[tulip_edge_devices:vars]
# Default configuration
tulip_factory_url=main.mfg.tulip.co
tulip_admin_email=admin@company.com
tulip_admin_password_sha256=default_hash_here

[production_floor:vars]
# Production uses main instance (inherits default)

[quality_control:vars]
# QC uses separate instance
tulip_factory_url=qc.mfg.tulip.co
tulip_admin_email=qc-admin@company.com
tulip_admin_password_sha256=qc_specific_hash
```

#### Per-Device Configuration

Individual devices can override settings:

```ini
[edge-device-special]
tulip_factory_url=special.mfg.tulip.co
tulip_admin_email=special-admin@company.com
tulip_admin_password_sha256=device_specific_hash
```

## Usage

### Simple Authentication

Authenticate a single device:
```bash
ansible-playbook -i inventory.ini collections/ansible_collections/tulip/edge/playbooks/gateway_tulip_auth.yml --limit device-name
```

### Bulk Authentication

Authenticate all devices in a group:
```bash
ansible-playbook -i inventory.ini collections/ansible_collections/tulip/edge/playbooks/gateway_tulip_auth.yml --limit production_floor
```

Authenticate all devices:
```bash
ansible-playbook -i inventory.ini collections/ansible_collections/tulip/edge/playbooks/gateway_tulip_auth.yml
```

## Expected Response

Upon successful authentication, you'll see output like:

```
Gateway Authentication Results for EIO-01-6B4FE843:
Status: Success

Gateway Details:
- Type: gateway
- Name: EIO-01-6B4FE843
- ID: muhmMHmaRiaLrtw95
- Hostname: edge-device-hostname
- API Key ID: apikey.2_HJzLyriFQ5hastsCb
- Replaced Existing: false
```

## Security Best Practices

1. **Never store plaintext passwords** - Always use SHA256 hashes
2. **Use different credentials per environment** - Production vs. staging vs. development
3. **Rotate passwords regularly** - Update hashes when passwords change
4. **Restrict inventory access** - Keep inventory files in secure version control
5. **Use per-device credentials** - For maximum security, use unique credentials per device

## Troubleshooting

### Missing Parameters Error

If you see this error:
```
Required parameters missing from inventory file
```

Add the required parameters to your inventory file under the appropriate section.

### Authentication Failed

Check:
1. Factory URL is correct (no `https://` prefix needed)
2. Admin email exists in the Tulip platform
3. Password hash is correct (regenerate if unsure)
4. Network connectivity to the factory URL

### API Connection Issues

Verify:
1. Device can reach the factory URL
2. Device authentication token is valid
3. Device API is accessible from Ansible control machine

## File Structure Example

Complete inventory file example:

```ini
[tulip_edge_devices]
EIO-01-6B4FE843 ansible_host=172.16.15.132
EIO-02-7C5GF954 ansible_host=172.16.15.133

[production_floor]
EIO-01-6B4FE843

[quality_control] 
EIO-02-7C5GF954

[tulip_edge_devices:vars]
edge_api_port=80
edge_use_https=false
edge_api_timeout=30
device_password="EdgeDevicePassword123"

# Tulip Factory Authentication
tulip_factory_url=company.mfg.tulip.co
tulip_admin_email=admin@company.com
tulip_admin_password_sha256=5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8

[quality_control:vars]
# QC devices use different Tulip instance
tulip_factory_url=qc.mfg.tulip.co
tulip_admin_email=qc-admin@company.com
tulip_admin_password_sha256=different_hash_for_qc_environment
```
