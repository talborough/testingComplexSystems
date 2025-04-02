import paramiko
import time
from shared_code import *

class HostConnectionManager:
    client_connections = []  # Class variable to store SSHClient objects

    @classmethod
    def create_host_connection(cls, host_ref):
        # Add None as placeholder for new connection
        cls.client_connections.append(None)
        # Create new host connection entry
        host_connection_ref = add_host_connection(host_ref, False)
        return host_connection_ref

    @classmethod
    def execute_on_host_connection(cls, host_connection_ref, command, debug=True, stop_on_error=True):
        host_ref = gHostConnection_gHost_Ref[host_connection_ref]
        
        # Ensure connection is valid
        if not gHostConnection_Valid[host_connection_ref]:
            while True:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(
                        gHost_IPAddress[host_ref],
                        username=gHost_Username[host_ref],
                        password=gHost_Password[host_ref]
                    )
                    cls.client_connections[host_connection_ref] = client
                    gHostConnection_Valid[host_connection_ref] = True
                    break
                except Exception as e:
                    if debug:
                        print(f"Connection attempt failed: {str(e)}")
                    time.sleep(1)

        if debug:
            print(f"Executing on host_ref: {host_ref}, connection_ref: {host_connection_ref}")
            print(f"Command: {command}")

        client = cls.client_connections[host_connection_ref]
        stdin, stdout, stderr = client.exec_command(command)
        
        stdout_str = stdout.read().decode().strip()
        stderr_str = stderr.read().decode().strip()

        if debug:
            if stdout_str:
                print(f"stdout: {stdout_str}")
            if stderr_str:
                print(f"stderr: {stderr_str}")

        if stop_on_error and stderr_str:
            raise Exception(f"Command failed: {stderr_str}")

        return stdin, stdout, stderr
