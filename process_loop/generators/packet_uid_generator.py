import multiprocessing


"""
Functions as the base class for generating uids
only one instance should exist at any point
"""

class uid_generator:
    def __init__(self) -> None:
        self._p_uin_n = multiprocessing.Value("i", 0)
        
    def generate(self) -> int:
        """
        Increments and returns the process uid
        """
        with self._p_uin_n.get_lock():
            self._p_uin_n.value += 1
            return self._p_uin_n.value
    
    def get_current_uid(self) -> int:
        """
        (DO NOT USE AS UID)
        returns the process uid 
        (DO NOT USE AS UID)
        """
        with self._p_uin_n.get_lock():
            return self._p_uin_n.value
