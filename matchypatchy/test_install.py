'''
Main Function

'''
from matchypatchy.gui import main_gui
from matchypatchy.database import mpdb


def main(filepath='matchypatchy.db'):
    mpDB = mpdb.MatchyPatchyDB(filepath)
    main_gui.main_display(mpDB)


if __name__ == "__main__":
    main()
