'''
Main Function

'''
#!/usr/bin/env python

from matchypatchy.database import mpdb

mpDB = mpdb.MatchyPatchyDB()
tables = mpDB.validate()
print(tables)

