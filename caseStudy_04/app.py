# Python 3.6 compliant
from shared_code import *


def create_states():
    state_names = [
        "AlphaState",
        "BetaState",
        "GammaState",
    ]
    stateRefs = []
    for name in state_names:
        stateRefs.append(add_gState(name, row_status=None))
    return stateRefs


def create_towns(stateRefs):
    # 6 towns, associate 2 with each state
    town_specs = [
        ("AlphaTown1", "10001", stateRefs[0]),
        ("AlphaTown2", "10002", stateRefs[0]),
        ("BetaTown1",  "20001", stateRefs[1]),
        ("BetaTown2",  "20002", stateRefs[1]),
        ("GammaTown1", "30001", stateRefs[2]),
        ("GammaTown2", "30002", stateRefs[2]),
    ]
    townRefs = []
    for name, zipc, sref in town_specs:
        townRefs.append(add_gTown(name, zipc, sref, row_status=None))
    return townRefs


def create_houses(townRefs):
    # 20 houses distributed across towns in round-robin
    houseRefs = []
    for i in range(20):
        townRef = townRefs[i % len(townRefs)]
        addr = "{} Main St".format(100 + i)
        houseRefs.append(add_gHouse(addr, townRef, row_status=None))
    return houseRefs


def create_people(houseRefs):
    # 40 people, 2 per house
    personRefs = []
    for i in range(40):
        name = "Person_{:02d}".format(i)
        dob = "199{:01d}-{:02d}-{:02d}".format(i % 10, (i % 12) + 1, ((i % 28) + 1))
        houseRef = houseRefs[i // 2]
        sex = "Male" if i % 2 == 0 else "Female"
        personRefs.append(add_gPerson(name, dob, houseRef, sex=sex, row_status=None))
    return personRefs


def pick_governors(personRefs, stateRefs):
    # Choose 5 distinct people as governors
    governor_persons = [personRefs[i] for i in [3, 7, 11, 15, 23]]

    # Ensure ~2/3 live-in-state ratio: mark first, second, and fourth to match living state; third and fifth mismatch
    match_flags = [True, True, False, True, False]

    # For each governor create 3 consecutive terms within 2020..2040
    # We'll use 2020-2023, 2024-2027, 2028-2031 per governor (3 terms)
    for idx, personRef in enumerate(governor_persons):
        # Determine the state they live in via cascading references
        houseRef = gPerson_gHouse_Ref[personRef]
        townRef = gHouse_gTown_Ref[houseRef]
        live_state_ref = gTown_gState_Ref[townRef]
        if match_flags[idx]:
            gov_state_ref = live_state_ref
        else:
            # pick a different state
            others = [s for s in stateRefs if s != live_state_ref]
            gov_state_ref = others[idx % len(others)]

        # Create 3 terms
        terms = [(2020, 2023), (2024, 2027), (2028, 2031)]
        for start, end in terms:
            add_gGovernor(gov_state_ref, personRef, start, end, row_status=None)

    # return mapping for clarity
    return governor_persons


def print_housemates_for_five(personRefs):
    # Given 5 people, print a list of the people living with each (exclude the given person)
    print("People and their housemates (excluding themselves):")
    sample = [personRefs[i] for i in [0, 5, 10, 20, 35]]
    for personRef in sample:  # for personRef in range(len(gPerson_RowStatus)):
        houseRef = gPerson_gHouse_Ref[personRef]
        housemates = []
        # iterate by reference type
        for otherPersonRef in range(len(gPerson_RowStatus)):
            if otherPersonRef == personRef:
                continue
            if gPerson_gHouse_Ref[otherPersonRef] == houseRef:
                housemates.append(gPerson_Name[otherPersonRef])
        print("- {}: {}".format(gPerson_Name[personRef], ", ".join(housemates) if housemates else "(no housemates)"))
    print("")


def print_governors_info():
    print("Governors (unsorted):")
    # Iterate over governor rows unsorted as stored
    for governorRef in range(len(gGovernor_RowStatus)):
        personRef = gGovernor_gPerson_Ref[governorRef]
        stateRef = gGovernor_gState_Ref[governorRef]
        term_start = gGovernor_TermStartDate[governorRef]
        term_end = gGovernor_TermEndDate[governorRef]
        # Cascading reference to find living state
        live_state_ref = gTown_gState_Ref[gHouse_gTown_Ref[gPerson_gHouse_Ref[personRef]]]
        mismatch = (live_state_ref != stateRef)

        print("Governor: {}".format(gPerson_Name[personRef]))
        print("  Governs State: {}".format(gState_Name[stateRef]))
        print("  Term: {}-{}".format(term_start, term_end))
        print("  Lives In State: {}".format(gState_Name[live_state_ref]))
        if mismatch:
            print("  *****")
    print("")


def main():
    # Creation steps: helper add_* already use gLock per instruction; avoid external wrapping to prevent deadlocks.
    stateRefs = create_states()
    townRefs = create_towns(stateRefs)
    houseRefs = create_houses(townRefs)
    personRefs = create_people(houseRefs)
    pick_governors(personRefs, stateRefs)

    # Outputs
    print_housemates_for_five(personRefs)
    print_governors_info()


if __name__ == "__main__":
    main()
