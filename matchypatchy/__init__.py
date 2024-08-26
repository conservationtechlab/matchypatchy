from matchypatchy import test_install
from matchypatchy import sqlite_vec

from matchypatchy.database import setup,mpdb
from matchypatchy.gui import (display_compare, display_intro)


from matchypatchy.database.setup import (setup_database)
from matchypatchy.database.mpdb import (MatchyPatchyDB)
from matchypatchy.gui.display_intro import (main, MainWindow)

__all__ = ['sqlite_vec', 'test_install', 'setup_database', 'MatchyPatchyDB', 'main', 'MainWindow']
