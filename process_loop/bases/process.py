import multiprocessing
import queue
import random
import time

from bases.packet import simple_packet
from generators.packet_uid_generator import uid_generator

class base_process(multiprocessing.Process):
    """
    Base process class, still under development
    """

    def __init__(self, my_send_queue:multiprocessing.Queue, my_recv_queue:multiprocessing.Queue, uid, process_uid_generator:uid_generator) -> None:
        super().__init__()
        
        self.uid = uid

        self._process_uid_generator = process_uid_generator # uid total currently
        self._my_send_queue = my_send_queue
        self._my_recv_queue = my_recv_queue
    

    def dump_queue(self) -> list:
        """
        Read whats sent to the process and dump it into an array
        """
        contents = []
        while True:
            try:
                # drain the queue
                contents.append(self._my_recv_queue.get(block=False))
            except queue.Empty as e:
                break
        return contents
    

    def put_in_queue(self, contents, targets="", target_type=[]) -> bool:
        """
        puts items into the queue for the main loop to read
        """
        p_uid_n = self._process_uid_generator.generate()
        p = simple_packet(p_uid_n, self.uid, contents, targets=targets, target_type=target_type)
        self._my_send_queue.put(p, block=False)


    def run(self):
        # imports

        # main loop

        try:
            counter = 0
            #update_time = time.time()
            #array = []
            while True:
                content = self.dump_queue()

                for i in content:
                    i:simple_packet
                    counter -= i.content

                v = random.random()/2 # *4 # 1,5
                #now = time.time()

                #update_time = now
                # send a debuff to another process
                if random.randint(0,1):
                    p_uid_n = self._process_uid_generator.generate()
                    p = simple_packet(p_uid_n, self.uid, random.randint(1,2), targets=(random.randint(0,15), ))
                    self._my_send_queue.put(p, block=False)
            

                p_uid_n = self._process_uid_generator.generate()
                p = simple_packet(p_uid_n, self.uid, [counter,v])
                self._my_send_queue.put(p, block=False)
                #array = []
                counter += 1
                if counter >= 16:
                    raise KeyboardInterrupt
                time.sleep(v)
        except KeyboardInterrupt as e:
            print(f"exiting id: {self.uid}")
        finally:
            self._my_send_queue.close()
            self._my_recv_queue.close()
