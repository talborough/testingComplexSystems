# Python 3.6 compliant
import multiprocessing

# Global Manager and single Lock
manager = multiprocessing.Manager()

# Define the single multiprocessing.Lock instance
gLock = multiprocessing.Lock()

# Helper to create manager-backed primitives
# Tables are columnar: each column is a manager.list(); indices are manager.dict(); singles are manager.Value

# ----------------------------
# gPerson Table
# ----------------------------
# Columns
gPerson_Name = manager.list()          # unique, has index
gPerson_DOB = manager.list()
gPerson_gHouse_Ref = manager.list()
gPerson_Sex = manager.list()           # default "Neither"
gPerson_RowStatus = manager.list()     # must be last created entry when adding rows

# Indices
gPerson_Name2Ref = manager.dict()      # name -> personRef, must be unique

# ----------------------------
# gHouse Table
# ----------------------------
# Columns
gHouse_Address = manager.list()        # unique, has index
gHouse_gTown_Ref = manager.list()
gHouse_RowStatus = manager.list()

# Indices
gHouse_Address2Ref = manager.dict()    # address -> houseRef, must be unique

# ----------------------------
# gTown Table
# ----------------------------
# Columns
gTown_Name = manager.list()            # unique, has index
gTown_ZipCode = manager.list()
gTown_gState_Ref = manager.list()
gTown_RowStatus = manager.list()

# Indices
gTown_Name2Ref = manager.dict()        # name -> townRef, must be unique

# ----------------------------
# gState Table
# ----------------------------
# Columns
gState_Name = manager.list()           # unique, has index
gState_RowStatus = manager.list()

# Indices
gState_Name2Ref = manager.dict()       # name -> stateRef, must be unique

# ----------------------------
# gGovernor Table
# ----------------------------
# Columns
gGovernor_gState_Ref = manager.list()
gGovernor_gPerson_Ref = manager.list()
gGovernor_TermStartDate = manager.list()
gGovernor_TermEndDate = manager.list()
gGovernor_RowStatus = manager.list()

# ----------------------------
# Unary / list / dict values
# ----------------------------
# Define unary gSomeValue 123
gSomeValue = manager.Value('i', 123)  # integer value

# Define list gSomeList
gSomeList = manager.list()

# Define dict gSomeDict
gSomeDict = manager.dict()


# ----------------------------
# Helper functions to add rows (use gLock as required). RowStatus must be appended last.
# ----------------------------

def _ensure_unique(index_dict, key, label):
    if key in index_dict:
        raise ValueError("Duplicate value for unique indexed column '{}': {}".format(label, key))


def add_gState(state_name, row_status=None):
    """Add a State. Unique on state_name. Returns stateRef (int)."""
    with gLock:
        _ensure_unique(gState_Name2Ref, state_name, 'gState_Name')
        stateRef = len(gState_Name)
        gState_Name.append(state_name)
        gState_RowStatus.append(row_status)
        # Update index after successful append
        gState_Name2Ref[state_name] = stateRef
        return stateRef


def add_gTown(town_name, zip_code, gState_Ref, row_status=None):
    """Add a Town. Unique on town_name. Returns townRef (int)."""
    with gLock:
        _ensure_unique(gTown_Name2Ref, town_name, 'gTown_Name')
        townRef = len(gTown_Name)
        gTown_Name.append(town_name)
        gTown_ZipCode.append(zip_code)
        gTown_gState_Ref.append(gState_Ref)
        gTown_RowStatus.append(row_status)
        gTown_Name2Ref[town_name] = townRef
        return townRef


def add_gHouse(address, gTown_Ref, row_status=None):
    """Add a House. Unique on address. Returns houseRef (int)."""
    with gLock:
        _ensure_unique(gHouse_Address2Ref, address, 'gHouse_Address')
        houseRef = len(gHouse_Address)
        gHouse_Address.append(address)
        gHouse_gTown_Ref.append(gTown_Ref)
        gHouse_RowStatus.append(row_status)
        gHouse_Address2Ref[address] = houseRef
        return houseRef


def add_gPerson(name, dob, gHouse_Ref, sex="Neither", row_status=None):
    """Add a Person. Unique on name. Returns personRef (int)."""
    with gLock:
        _ensure_unique(gPerson_Name2Ref, name, 'gPerson_Name')
        personRef = len(gPerson_Name)
        gPerson_Name.append(name)
        gPerson_DOB.append(dob)
        gPerson_gHouse_Ref.append(gHouse_Ref)
        gPerson_Sex.append(sex)
        gPerson_RowStatus.append(row_status)
        gPerson_Name2Ref[name] = personRef
        return personRef


def add_gGovernor(gState_Ref, gPerson_Ref, term_start_date, term_end_date, row_status=None):
    """Add a Governor row. Returns governorRef (int)."""
    with gLock:
        governorRef = len(gGovernor_gState_Ref)
        gGovernor_gState_Ref.append(gState_Ref)
        gGovernor_gPerson_Ref.append(gPerson_Ref)
        gGovernor_TermStartDate.append(term_start_date)
        gGovernor_TermEndDate.append(term_end_date)
        gGovernor_RowStatus.append(row_status)
        return governorRef


# ----------------------------
# Lookup helpers (indices)
# ----------------------------

def find_state_ref_by_name(name):
    return gState_Name2Ref.get(name)


def find_town_ref_by_name(name):
    return gTown_Name2Ref.get(name)


def find_house_ref_by_address(addr):
    return gHouse_Address2Ref.get(addr)


def find_person_ref_by_name(name):
    return gPerson_Name2Ref.get(name)
