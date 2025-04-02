from multiprocessing import Manager
from datetime import datetime

# Initialize manager
manager = Manager()

# Tables and indices
gPerson_Name = manager.list()
gPerson_DOB = manager.list()
gPerson_gHouse_Ref = manager.list()
gPerson_Sex = manager.list()
gPerson_Name2Ref = manager.dict()

gHouse_Address = manager.list()
gHouse_gTown_Ref = manager.list()
gHouse_Address2Ref = manager.dict()

gTown_Name = manager.list()
gTown_ZipCode = manager.list()
gTown_gState_Ref = manager.list()
gTown_Name2Ref = manager.dict()

gState_Name = manager.list()
gState_Name2Ref = manager.dict()

gGovernor_gState_Ref = manager.list()
gGovernor_gPerson_Ref = manager.list()
gGovernor_TermStartDate = manager.list()
gGovernor_TermEndDate = manager.list()

# Single values and collections
gSomeValue = manager.Value('i', 123)
gSomeList = manager.list()
gSomeDict = manager.dict()

def add_person(name, dob, house_ref=None, sex="Neither"):
    if name in gPerson_Name2Ref:
        raise Exception(f"Person {name} already exists")
    ref = len(gPerson_Name)
    gPerson_Name.append(name)
    gPerson_DOB.append(dob)
    gPerson_gHouse_Ref.append(house_ref)
    gPerson_Sex.append(sex)
    gPerson_Name2Ref[name] = ref
    return ref

def add_house(address, town_ref=None):
    if address in gHouse_Address2Ref:
        raise Exception(f"House {address} already exists")
    ref = len(gHouse_Address)
    gHouse_Address.append(address)
    gHouse_gTown_Ref.append(town_ref)
    gHouse_Address2Ref[address] = ref
    return ref

def add_town(name, zipcode, state_ref=None):
    if name in gTown_Name2Ref:
        raise Exception(f"Town {name} already exists")
    ref = len(gTown_Name)
    gTown_Name.append(name)
    gTown_ZipCode.append(zipcode)
    gTown_gState_Ref.append(state_ref)
    gTown_Name2Ref[name] = ref
    return ref

def add_state(name):
    if name in gState_Name2Ref:
        raise Exception(f"State {name} already exists")
    ref = len(gState_Name)
    gState_Name.append(name)
    gState_Name2Ref[name] = ref
    return ref

def add_governor(state_ref, person_ref, term_start, term_end):
    ref = len(gGovernor_gState_Ref)
    gGovernor_gState_Ref.append(state_ref)
    gGovernor_gPerson_Ref.append(person_ref)
    gGovernor_TermStartDate.append(term_start)
    gGovernor_TermEndDate.append(term_end)
    return ref

def get_housemates(person_ref):
    house_ref = gPerson_gHouse_Ref[person_ref]
    if house_ref is None:
        return []
    return [ref for ref in range(len(gPerson_Name)) 
            if gPerson_gHouse_Ref[ref] == house_ref and ref != person_ref]

def get_person_state(person_ref):
    house_ref = gPerson_gHouse_Ref[person_ref]
    if house_ref is None:
        return None
    town_ref = gHouse_gTown_Ref[house_ref]
    if town_ref is None:
        return None
    return gTown_gState_Ref[town_ref]

def print_governor_info():
    for gov_ref in range(len(gGovernor_gState_Ref)):
        person_ref = gGovernor_gPerson_Ref[gov_ref]
        state_ref = gGovernor_gState_Ref[gov_ref]
        person_state = get_person_state(person_ref)
        
        print(f"Governor: {gPerson_Name[person_ref]}")
        print(f"Governs State: {gState_Name[state_ref]}")
        print(f"Term: {gGovernor_TermStartDate[gov_ref]} to {gGovernor_TermEndDate[gov_ref]}")
        print(f"Lives in State: {gState_Name[person_state] if person_state is not None else 'Unknown'}")
        if person_state != state_ref:
            print("*****")
        print()

# Initialize data
def create_sample_data():
    # Create states
    states = ["California", "Texas", "New York"]
    state_refs = [add_state(name) for name in states]

    # Create towns (2 per state)
    towns = [
        ("San Francisco", "94101"), ("Los Angeles", "90001"),
        ("Austin", "73301"), ("Houston", "77001"),
        ("New York City", "10001"), ("Buffalo", "14201")
    ]
    town_refs = []
    for i, (name, zip_code) in enumerate(towns):
        town_refs.append(add_town(name, zip_code, state_refs[i // 2]))

    # Create houses
    houses = [f"{i+1} Main St" for i in range(20)]
    house_refs = []
    for i, address in enumerate(houses):
        house_refs.append(add_house(address, town_refs[i % 6]))

    # Create people
    for i in range(40):
        name = f"Person{i+1}"
        dob = f"{1960 + i % 30}-01-01"
        house_ref = house_refs[i % 20]
        add_person(name, dob, house_ref)

    # Create governors
    governor_data = [
        (0, "2020-01-01", "2024-12-31"),
        (0, "2025-01-01", "2029-12-31"),
        (0, "2030-01-01", "2034-12-31"),
        (1, "2020-01-01", "2024-12-31"),
        (1, "2025-01-01", "2029-12-31"),
        (1, "2030-01-01", "2034-12-31"),
        (2, "2020-01-01", "2024-12-31"),
        (2, "2025-01-01", "2029-12-31"),
        (2, "2030-01-01", "2034-12-31"),
    ]
    
    # Assign governors (using first 5 people as governors)
    governor_people = [i for i in range(5)]
    term_index = 0
    for gov_person in governor_people:
        for _ in range(2 if gov_person < 3 else 1):  # First 3 governors get 2 terms, last 2 get 1 term
            if term_index >= len(governor_data):
                break
            state_ref, start_date, end_date = governor_data[term_index]
            add_governor(state_ref, gov_person, start_date, end_date)
            term_index += 1

def print_housemates_for_people(people_refs):
    for person_ref in people_refs:
        print(f"\nHousemates for {gPerson_Name[person_ref]}:")
        housemates = get_housemates(person_ref)
        if not housemates:
            print("  None")
        else:
            for housemate_ref in housemates:
                print(f"  {gPerson_Name[housemate_ref]}")
