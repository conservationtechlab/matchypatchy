'''
Main Function

'''
#!/usr/bin/env python

from matchypatchy.database import mpdb
from matchypatchy.gui import display_intro

mpDB = mpdb.MatchyPatchyDB()
tables = mpDB.validate()
display_intro.main_display(mpDB)


