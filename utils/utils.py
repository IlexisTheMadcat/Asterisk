from typing import List


ZWSP = "​"

def fetch_array_item(list_array: List[list], x: int, y:int, one_based=True):
    """Get item from a list of lists. Simple arrays."""
    return list_array[y-1 if one_based else y][x-1 if one_based else x]

def set_array_item(list_array: List[list], x: int, y:int, new_value, one_based=True):
    """Set an item in a list of lists. Simple arrays."""
    list_array[y-1 if one_based else y][x-1 if one_based else x] = new_value
    return list_array
