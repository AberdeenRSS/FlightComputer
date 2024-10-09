class base_packet:
    """
    uid is the one created by "use process uid number" (i'll implement a way to properly generate this)
    the very basic packet class, targets & target_type are optional
    """

    def __init__(self, uid:int, sender_uid:int, targets:list=[], target_type:str="") -> None:
        self.uid = uid
        self.sender_uid = sender_uid
        self.targets = targets
        self.target_type = target_type
        

class simple_packet(base_packet):
    """
    an example packet class with one variable "content" allowing anything to be assigned to it
    """
    def __init__(self, uid: int, sender_uid:int, content, targets: list = [], target_type: str = "") -> None:
        super().__init__(uid, sender_uid, targets, target_type)

        self.content = content