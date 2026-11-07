# Release notes for the code in the testingComplexSystems repo

See the LinkedIn group Testing Complex Systems for additional information.

## 11/06/2026

- Fix all combinations of Linux and Windows gDS executions needed for 10/27/2026's fix. Note that gDS multiprocessing code still does not run on Windows but schemas that do not use gDS multiprocessing functionality can still be compiled into .py code that will run on both operating systems.

**YOUR `.dd` FILES MUST BE RE-COMPILED WITH THIS NEW gDS V2 COMPILER VERSION IN ORDER FOR THIS FIX TO TAKE EFFECT!!**

(Bug reports welcome.)

## 11/02/2026

- Add some release notes - this file.

## 10/30/2026

- Rename Case Study 3 so people know not to run it without updating it.
- Start Case Study 5: a test platform for Oracle software.

## 10/27/2026

- Make the V2 compiler generate code to set which "fork" method to use at runtime. Required for Python 3.14 and above.

**YOUR `.dd` FILES MUST BE RE-COMPILED WITH THIS NEW COMPILER VERSION IN ORDER FOR THIS TO TAKE EFFECT!!**

