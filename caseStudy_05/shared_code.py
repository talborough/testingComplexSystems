from multiprocessing import Manager, Lock

# Initialize manager and lock
manager = Manager()
global_lock = Lock()

# Host table
gHost_IPAddress = manager.list()
gHost_Username = manager.list()
gHost_Password = manager.list()
gHost_Hostname = manager.list()
gHost_HostString = manager.list()
gHost_IPAddress2Ref = manager.dict()

# Host Connection table
gHostConnection_gHost_Ref = manager.list()
gHostConnection_Valid = manager.list()

# Single values
gSomeValue = manager.Value('i', 123)

# Additional structures
gSomeList = manager.list()
gSomeDict = manager.dict()

def add_host(ip_address, username, password, hostname=None, host_string=None):
    with global_lock:
        if ip_address in gHost_IPAddress2Ref:
            raise Exception(f"Host with IP {ip_address} already exists")
        
        ref = len(gHost_IPAddress)
        gHost_IPAddress.append(ip_address)
        gHost_Username.append(username)
        gHost_Password.append(password)
        gHost_Hostname.append(hostname)
        gHost_HostString.append(host_string)
        gHost_IPAddress2Ref[ip_address] = ref
        return ref

def add_host_connection(host_ref, valid=False):
    with global_lock:
        ref = len(gHostConnection_gHost_Ref)
        gHostConnection_gHost_Ref.append(host_ref)
        gHostConnection_Valid.append(valid)
        return ref
