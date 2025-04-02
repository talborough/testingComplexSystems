#!/usr/bin/env python3
from shared_code import *
from host_connection_manager import HostConnectionManager

def parse_config():
    hosts = {}
    current_host = None
    
    with open('TPBase.conf', 'r') as f:
        for line in f:
            line = line.split('#')[0].strip()  # Remove comments
            if not line:
                continue
                
            if '=' in line:
                key, value = [x.strip() for x in line.split('=', 1)]
                if '.' in key:
                    host_id, param = key.split('.')
                    if host_id not in hosts:
                        hosts[host_id] = {}
                    hosts[host_id][param] = value

    # Add hosts to the table
    for host_data in hosts.values():
        add_host(
            ip_address=host_data['ipaddress'],
            username=host_data['username'],
            password=host_data['password']
        )

def main():
    # Parse configuration
    parse_config()
    
    # Get hostnames and set host strings
    for host_ref in range(len(gHost_IPAddress)):
        conn_ref = HostConnectionManager.create_host_connection(host_ref)
        _, stdout, _ = HostConnectionManager.execute_on_host_connection(conn_ref, "hostname")
        hostname = stdout.read().decode().strip()
        
        with global_lock:
            gHost_Hostname[host_ref] = hostname
            gHost_HostString[host_ref] = hostname[-4:] if len(hostname) >= 4 else hostname

if __name__ == "__main__":
    main()
