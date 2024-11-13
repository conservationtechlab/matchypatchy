"""
Collection of utility functions
"""


def swap_keyvalue(dictionary):
    return dict((v, k) for k, v in dictionary.items())


def is_unique(vector):
    a = vector.to_numpy()  # s.values (pandas<0.24)
    return (a[0] == a).all()
