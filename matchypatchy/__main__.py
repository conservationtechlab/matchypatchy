'''
Main Function

'''

from .gui import display_intro
from .database import mpdb


def main(filepath='matchypatchy.db'):
    mpDB = mpdb.MatchyPatchyDB(filepath)
    display_intro.main_display(mpDB)


if __name__ == "__main__":
    main()