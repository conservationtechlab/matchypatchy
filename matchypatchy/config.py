import os
import tempfile


tempfile.tempdir = tempfile.mkdtemp(prefix="MatchyPatchy_")

LOGFILE = os.path.join(os.getcwd(), 'matchpatchy.log')
DB_PATH = os.path.join(os.getcwd(), 'matchypatchy.db')
TEMPDIR =tempfile.gettempdir()
