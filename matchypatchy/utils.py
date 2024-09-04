"""
Collection of utility functions
"""

def swap_keyvalue(dictionary):
    return dict((v,k) for k,v in dictionary.items())