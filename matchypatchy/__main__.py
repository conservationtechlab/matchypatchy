'''
Main Function

'''

from .gui import display_intro
from .database import setup

def main():
    mpDB = setup.MatchyPatchyDB()
    display_intro.main(mpDB)
    tables = setup.validate()
    print(tables)

if __name__ == "__main__":
    main()