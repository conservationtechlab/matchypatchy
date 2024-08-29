"""
Functions for Importing and Manipulating Media
"""

import pandas as pd


def import_animl(mpdb, manifest_filepath):
    # ADD DTYPE CHECKS
    manifest = pd.read_csv(manifest_filepath)
    
    
    
    mpdb.add_media(filepath,ext)
    
    
    
    
    '''CREATE TABLE IF NOT EXISTS media (
                        id INTEGER PRIMARY KEY,
                        filepath TEXT NOT NULL,
                        ext TEXT NOT NULL,
                        datetime TEXT,
                        comment TEXT,
                        site_id INTEGER NOT NULL,
                        FOREIGN KEY (site_id) REFERENCES site (id) )'''
                        
    