# To consume this file in a Python program:

#     exec (open('animalFarm_02.py').read())

# Start of gDS include file ...

from multiprocessing import Manager
import json
gDSMgr = Manager()

#
# Define global shared variables for entity gCounty
#
gCounty_Name = gDSMgr.list()
gCounty_RowStatus = gDSMgr.list()

#
# Define global shared variables for entity gFarm
#
gFarm_Name = gDSMgr.list()
gFarm_gCounty_Ref = gDSMgr.list()
gFarm_MilkTotal = gDSMgr.list()
gFarm_EggsTotal = gDSMgr.list()
gFarm_RowStatus = gDSMgr.list()

#
# Define global shared variables for entity gAnimal
#
gAnimal_gFarm_Ref = gDSMgr.list()
gAnimal_Type = gDSMgr.list()
gAnimal_Name = gDSMgr.list()
gAnimal_Time = gDSMgr.list()
gAnimal_Produced = gDSMgr.list()
gAnimal_Name2Ref = gDSMgr.dict()
gAnimal_Time2Ref = gDSMgr.dict()
gAnimal_RowStatus = gDSMgr.list()

gTotalMilkCalculated = gDSMgr.list()
gTotalMilkCalculated.append(0)

gTotalMilkObserved = gDSMgr.list()
gTotalMilkObserved.append(0)

gTotalEggsCalculated = gDSMgr.list()
gTotalEggsCalculated.append(0)

gTotalEggsObserved = gDSMgr.list()
gTotalEggsObserved.append(0)

gTotalAnimalsCalculated = gDSMgr.list()
gTotalAnimalsCalculated.append(0)

gTotalAnimalsObserved = gDSMgr.list()
gTotalAnimalsObserved.append(0)

gStartTime = gDSMgr.list()
gStartTime.append(0)

gStopBackgroundProcs = gDSMgr.list()
gStopBackgroundProcs.append(True)

gMakeTestRun = gDSMgr.list()
gMakeTestRun.append(False)

gRunStopTime = gDSMgr.list()
gRunStopTime.append(0)

gCycleStopTime = gDSMgr.list()
gCycleStopTime.append(0)

gBatchMode = gDSMgr.list()
gBatchMode.append(False)

gScreenLines = gDSMgr.list()
gScreenLines.append("")

#
# Add a row to table gCounty
#
def gCounty_AddARow(\
    _RowStatus,\
    _Name = None,\
):

    gCounty_Name.append(_Name)
    gCounty_RowStatus.append(_RowStatus)

    return (len(gCounty_RowStatus) - 1)

#
# Add a row to table gFarm
#
def gFarm_AddARow(\
    _gCounty_Ref,\
    _RowStatus,\
    _Name = None,\
    _MilkTotal = 0,\
    _EggsTotal = 0,\
):

    gFarm_Name.append(_Name)
    gFarm_gCounty_Ref.append(_gCounty_Ref)
    gFarm_MilkTotal.append(_MilkTotal)
    gFarm_EggsTotal.append(_EggsTotal)
    gFarm_RowStatus.append(_RowStatus)

    return (len(gFarm_RowStatus) - 1)

#
# Add a row to table gAnimal
#
def gAnimal_AddARow(\
    _gFarm_Ref,\
    _Type,\
    _Time,\
    _RowStatus,\
    _Name = None,\
    _Produced = 0,\
):

    gAnimal_gFarm_Ref.append(_gFarm_Ref)
    gAnimal_Type.append(_Type)
    gAnimal_Name.append(_Name)
    gAnimal_Time.append(_Time)
    gAnimal_Produced.append(_Produced)
    gAnimal_RowStatus.append(_RowStatus)

    thisRef = len(gAnimal_RowStatus) - 1

    if gAnimal_Name[thisRef] in gAnimal_Name2Ref:
        print('')
        raise KeyError('Duplicate key in gAnimal_Name2Ref; value = ', gAnimal_Name[thisRef])
        print('')

    gAnimal_Name2Ref[gAnimal_Name[thisRef]] = thisRef

    if gAnimal_Time[thisRef] in gAnimal_Time2Ref:
        print('')
        raise KeyError('Duplicate key in gAnimal_Time2Ref; value = ', gAnimal_Time[thisRef])
        print('')

    gAnimal_Time2Ref[gAnimal_Time[thisRef]] = thisRef

    return (len(gAnimal_RowStatus) - 1)

#
# Delete erased rows in table gCounty
#
def gCounty_DeleteRows(rowStatusValueToDelete = '!All!'):

    for rowRef in range(len(gCounty_RowStatus) - 1, -1, -1):
        if (rowStatusValueToDelete == '!All!') or (gCounty_RowStatus[rowRef] == rowStatusValueToDelete):
            del gCounty_Name[rowRef]
            del gCounty_RowStatus[rowRef]

        else:
            pass


    return (len(gCounty_RowStatus))

#
# Delete erased rows in table gFarm
#
def gFarm_DeleteRows(rowStatusValueToDelete = '!All!'):

    for rowRef in range(len(gFarm_RowStatus) - 1, -1, -1):
        if (rowStatusValueToDelete == '!All!') or (gFarm_RowStatus[rowRef] == rowStatusValueToDelete):
            del gFarm_Name[rowRef]
            del gFarm_gCounty_Ref[rowRef]
            del gFarm_MilkTotal[rowRef]
            del gFarm_EggsTotal[rowRef]
            del gFarm_RowStatus[rowRef]

        else:
            pass


    return (len(gFarm_RowStatus))

#
# Delete erased rows in table gAnimal
#
def gAnimal_DeleteRows(rowStatusValueToDelete = '!All!'):

    for rowRef in range(len(gAnimal_RowStatus) - 1, -1, -1):
        if (rowStatusValueToDelete == '!All!') or (gAnimal_RowStatus[rowRef] == rowStatusValueToDelete):
            del gAnimal_gFarm_Ref[rowRef]
            del gAnimal_Type[rowRef]
            del gAnimal_Name[rowRef]
            del gAnimal_Time[rowRef]
            del gAnimal_Produced[rowRef]
            del gAnimal_RowStatus[rowRef]

        else:
            pass

    gAnimal_Name2Ref.clear()
    gAnimal_Time2Ref.clear()
    for rowRef in range(len(gAnimal_RowStatus)):
        gAnimal_Name2Ref[gAnimal_Name[rowRef]] = rowRef
        gAnimal_Time2Ref[gAnimal_Time[rowRef]] = rowRef

    return (len(gAnimal_RowStatus))

#
# Print values out for table 'gCounty'
#
def gCounty_DumpRows(rangeListToDump = None, outFile = sys.stdout):

    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print('    Table %s has %d entries' % ('gCounty', len(gCounty_RowStatus)), file = outFile)
    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print(f'', file = outFile)

    for rowRef in range(0, len(gCounty_RowStatus)):
        if (rangeListToDump is None) or (rowRef in rangeListToDump):
            print('    Row reference = %d' % (rowRef), file = outFile)
            print('    %30s = %10s' % ('gCounty_Name', gCounty_Name[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gCounty_RowStatus', gCounty_RowStatus[rowRef]), file = outFile)
            print('', file = outFile)

    return


#
# Print values out for table 'gFarm'
#
def gFarm_DumpRows(rangeListToDump = None, outFile = sys.stdout):

    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print('    Table %s has %d entries' % ('gFarm', len(gFarm_RowStatus)), file = outFile)
    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print(f'', file = outFile)

    for rowRef in range(0, len(gFarm_RowStatus)):
        if (rangeListToDump is None) or (rowRef in rangeListToDump):
            print('    Row reference = %d' % (rowRef), file = outFile)
            print('    %30s = %10s' % ('gFarm_Name', gFarm_Name[rowRef]), file = outFile)
            print('    %30s = %10s  (%30s)' % ('gFarm_gCounty_Ref', gFarm_gCounty_Ref[rowRef], gCounty_Name[gFarm_gCounty_Ref[rowRef]]), file = outFile)
            print('    %30s = %10s' % ('gFarm_MilkTotal', gFarm_MilkTotal[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gFarm_EggsTotal', gFarm_EggsTotal[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gFarm_RowStatus', gFarm_RowStatus[rowRef]), file = outFile)
            print('', file = outFile)

    return


#
# Print values out for table 'gAnimal'
#
def gAnimal_DumpRows(rangeListToDump = None, outFile = sys.stdout):

    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print('    Table %s has %d entries' % ('gAnimal', len(gAnimal_RowStatus)), file = outFile)
    print(f'**************', file = outFile)
    print(f'**************', file = outFile)
    print(f'', file = outFile)

    for rowRef in range(0, len(gAnimal_RowStatus)):
        if (rangeListToDump is None) or (rowRef in rangeListToDump):
            print('    Row reference = %d' % (rowRef), file = outFile)
            print('    %30s = %10s  (%30s)' % ('gAnimal_gFarm_Ref', gAnimal_gFarm_Ref[rowRef], gFarm_Name[gAnimal_gFarm_Ref[rowRef]]), file = outFile)
            print('    %30s = %10s' % ('gAnimal_Type', gAnimal_Type[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gAnimal_Name', gAnimal_Name[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gAnimal_Time', gAnimal_Time[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gAnimal_Produced', gAnimal_Produced[rowRef]), file = outFile)
            print('    %30s = %10s' % ('gAnimal_RowStatus', gAnimal_RowStatus[rowRef]), file = outFile)
            if gAnimal_Name2Ref[gAnimal_Name[rowRef]] != rowRef:
                raise ValueError('Bad index value in gAnimal_Name2Ref; value = ' + str(gAnimal_Name[rowRef]))
            else:
                print(f"                    Good index value in gAnimal_Name2Ref[{gAnimal_Name[rowRef]!r}]: {rowRef}", file = outFile)
            if gAnimal_Time2Ref[gAnimal_Time[rowRef]] != rowRef:
                raise ValueError('Bad index value in gAnimal_Time2Ref; value = ' + str(gAnimal_Time[rowRef]))
            else:
                print(f"                    Good index value in gAnimal_Time2Ref[{gAnimal_Time[rowRef]!r}]: {rowRef}", file = outFile)
            print('', file = outFile)

    return


#
# Write table 'gCounty' to a JSON file
#
def gCounty_WriteToFile(filePath, rangeListToDump=None):
    rows = []
    for i in range(len(gCounty_RowStatus)):
        if (rangeListToDump is None) or (i in rangeListToDump):
            row = {}
            row['gCounty_Name'] = gCounty_Name[i]
            row['gCounty_RowStatus'] = gCounty_RowStatus[i]
            rows.append(row)
    with open(filePath, 'w') as f:
        json.dump(rows, f, indent=2)
    return


#
# Write table 'gFarm' to a JSON file
#
def gFarm_WriteToFile(filePath, rangeListToDump=None):
    rows = []
    for i in range(len(gFarm_RowStatus)):
        if (rangeListToDump is None) or (i in rangeListToDump):
            row = {}
            row['gFarm_Name'] = gFarm_Name[i]
            row['gFarm_gCounty_Ref'] = gFarm_gCounty_Ref[i]
            row['gFarm_MilkTotal'] = gFarm_MilkTotal[i]
            row['gFarm_EggsTotal'] = gFarm_EggsTotal[i]
            row['gFarm_RowStatus'] = gFarm_RowStatus[i]
            rows.append(row)
    with open(filePath, 'w') as f:
        json.dump(rows, f, indent=2)
    return


#
# Write table 'gAnimal' to a JSON file
#
def gAnimal_WriteToFile(filePath, rangeListToDump=None):
    rows = []
    for i in range(len(gAnimal_RowStatus)):
        if (rangeListToDump is None) or (i in rangeListToDump):
            row = {}
            row['gAnimal_gFarm_Ref'] = gAnimal_gFarm_Ref[i]
            row['gAnimal_Type'] = gAnimal_Type[i]
            row['gAnimal_Name'] = gAnimal_Name[i]
            row['gAnimal_Time'] = gAnimal_Time[i]
            row['gAnimal_Produced'] = gAnimal_Produced[i]
            row['gAnimal_RowStatus'] = gAnimal_RowStatus[i]
            rows.append(row)
    with open(filePath, 'w') as f:
        json.dump(rows, f, indent=2)
    return


#
# Read table 'gCounty' from a JSON file
#
def gCounty_ReadFromFile(filePath):
    with open(filePath) as f:
        rows = json.load(f)
    for row in rows:
        gCounty_AddARow(row['gCounty_RowStatus'], row.get('gCounty_Name', None))
    return


#
# Read table 'gFarm' from a JSON file
#
def gFarm_ReadFromFile(filePath):
    with open(filePath) as f:
        rows = json.load(f)
    for row in rows:
        gFarm_AddARow(row['gFarm_gCounty_Ref'], row['gFarm_RowStatus'], row.get('gFarm_Name', None), row.get('gFarm_MilkTotal', 0), row.get('gFarm_EggsTotal', 0))
    return


#
# Read table 'gAnimal' from a JSON file
#
def gAnimal_ReadFromFile(filePath):
    with open(filePath) as f:
        rows = json.load(f)
    for row in rows:
        gAnimal_AddARow(row['gAnimal_gFarm_Ref'], row['gAnimal_Type'], row['gAnimal_Time'], row['gAnimal_RowStatus'], row.get('gAnimal_Name', None), row.get('gAnimal_Produced', 0))
    return

