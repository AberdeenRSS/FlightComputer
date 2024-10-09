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
        
        self.process_uid_generator = process_uid_generator # uid total currently
        self.uid = uid
        self.my_send_queue = my_send_queue
        self.my_recv_queue = my_recv_queue
    
    def run(self):
        # imports

        # main loop

        try:
            counter = 0
            #update_time = time.time()
            #array = []
            while True:
                # read whats sent to this process and do stuff with it
                while True:
                    try:
                        # drain the queue
                        temp:simple_packet = self.my_recv_queue.get(block=False)
                        counter -= temp.content
                    except queue.Empty as e:
                        break


                v = random.random()/2 # *4 # 1,5
                #now = time.time()

                #update_time = now
                # send a debuff to another process
                if random.randint(0,1):
                    p_uid_n = self.process_uid_generator.generate()
                    p = simple_packet(p_uid_n, self.uid, random.randint(1,2), targets=(random.randint(0,15), ))
                    self.my_send_queue.put(p, block=False)
            

                p_uid_n = self.process_uid_generator.generate()
                p = simple_packet(p_uid_n, self.uid, [counter,v])
                self.my_send_queue.put(p, block=False)
                #array = []
                counter += 1
                if counter >= 16:
                    raise KeyboardInterrupt
                time.sleep(v)
        except KeyboardInterrupt as e:
            print(f"exiting id: {self.uid}")
        finally:
            self.my_send_queue.close()
            self.my_recv_queue.close()
