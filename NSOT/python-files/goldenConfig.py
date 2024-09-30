import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# Dynamically construct the CSV file path relative to the script location
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(CURRENT_DIR, '..', 'IPAM', 'hosts.csv')

# Directory to save golden configs
OUTPUT_DIR = os.path.join(CURRENT_DIR, '..', 'golden_configs')

def fetch_and_save_config(device_info):
    """Fetch running config and save it to a file."""
    print(f"Starting to process device: {device_info['hostname']}")

    device = {
        'device_type': 'cisco_ios',  # Assuming Cisco IOS device; modify based on the actual device type
        'ip': device_info['management_ip'],
        'username': device_info['username'],
        'password': device_info['password'],
        'secret': device_info['password']  # Adding enable password (assuming it’s the same as the login password)
    }

    try:
        # Establish SSH connection
        print(f"Connecting to {device_info['hostname']} at {device['ip']}...")
        ssh_conn = ConnectHandler(**device)
        print(f"Successfully connected to {device_info['hostname']}")

        # Enter privileged mode (if required)
        print(f"Attempting to enter privileged mode on {device_info['hostname']}...")
        ssh_conn.enable()  # This command enters privileged EXEC mode (enabled mode)
        print(f"Entered privileged mode on {device_info['hostname']}")

        # Fetch the running config
        print(f"Fetching running config from {device_info['hostname']}...")
        running_config = ssh_conn.send_command("show running-config")
        ssh_conn.disconnect()

        # Save the config to the file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"goldenconfigs_{device_info['hostname']}_{timestamp}.cfg"
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(output_path, 'w') as file:
            file.write(running_config)
        print(f"Config saved to {output_path}")
        return filename  # Return the filename for display
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        print(f"Failed to fetch config from {device_info['hostname']}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred with {device_info['hostname']}: {e}")
        return None

def fetch_configs_from_csv():
    """Fetch configs from all devices listed in the CSV."""
    print("Fetching device configurations from CSV...")
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    device_list = []
    with open(CSV_FILE_PATH, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            device_info = {
                'hostname': row['hostname'],
                'username': row['username'],
                'password': row['password'],
                'management_ip': row['management_ip']
            }
            device_list.append(device_info)  # Append device info to list
            print(f"Added device {row['hostname']} to the device list.")
    
    print(f"Total devices fetched from CSV: {len(device_list)}")
    return device_list

def fetch_config_for_device(hostname):
    """Fetch config for a specific device by hostname."""
    print(f"Fetching config for device: {hostname}")
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    with open(CSV_FILE_PATH, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['hostname'] == hostname:
                print(f"Found device {hostname} in the CSV.")
                device_info = {
                    'hostname': row['hostname'],
                    'username': row['username'],
                    'password': row['password'],
                    'management_ip': row['management_ip']
                }
                return fetch_and_save_config(device_info)
    
    print(f"Device {hostname} not found in the CSV.")
    return None

def generate_configs(select_all=False, hostname=None):
    """Main function to generate golden configs."""
    filenames = []
    if select_all:
        # Fetch configs from all devices in parallel
        print("Generating configs for all devices (parallel execution)...")
        devices = fetch_configs_from_csv()
        with ThreadPoolExecutor(max_workers=5) as executor:
            filenames = list(executor.map(fetch_and_save_config, devices))
    elif hostname:
        # Fetch config for a specific device
        print(f"Generating config for device: {hostname}")
        filename = fetch_config_for_device(hostname)
        if filename:
            filenames.append(filename)
    print(f"Config generation complete. Files created: {filenames}")
    return filenames
