'''
Main Function

'''
#!/usr/bin/env python

from matchypatchy.database import setup

mpDB = setup.MatchyPatchyDB()
tables = mpDB.validate()
print(tables)

