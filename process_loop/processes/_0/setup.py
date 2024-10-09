from multiprocessing import Queue
from bases.process import base_process

class custom_process(base_process):
    def __init__(self, my_send_queue: Queue, my_recv_queue: Queue, uid, process_uid_number) -> None:
        super().__init__(my_send_queue, my_recv_queue, uid, process_uid_number)