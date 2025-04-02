#!/usr/bin/env python3
from multiprocessing import Process
from shared_code import *
from host_connection_manager import HostConnectionManager

def execute_ls(host_connection_ref):
    HostConnectionManager.execute_on_host_connection(host_connection_ref, "ls -al")

def main():
    # Parse configuration first
    from main import parse_config
    parse_config()
    
    processes = []
    
    # Create 3 connections per host and start processes
    for host_ref in range(len(gHost_IPAddress)):
        for _ in range(3):  # Create 3 connections per host
            conn_ref = HostConnectionManager.create_host_connection(host_ref)
            p = Process(target=execute_ls, args=(conn_ref,))
            processes.append(p)
            p.start()
    
    # Wait for all processes to complete
    for p in processes:
        p.join()

if __name__ == "__main__":
    main()
