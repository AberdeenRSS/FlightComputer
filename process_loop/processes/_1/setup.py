
import queue
import random
import time

from bases.process import base_process
from generators.packet_uid_generator import uid_generator

from bases.packet import simple_packet

class custom_process(base_process):
    def __init__(self, my_send_queue: queue, my_recv_queue: queue, process_uid_generator:uid_generator, uid) -> None:
        # in file 1
        # therefore
        uid = 1
        super().__init__(my_send_queue, my_recv_queue, process_uid_generator, uid)

    def run(self):
        # imports

        # main loop
        # put ready command in queue so main system knows this function is ready
        print(f"{self.uid} ready")
        self.put_in_queue("ready")
        print(f"{self.uid} waiting for go")
        if self._my_recv_queue.get() != "go":
            return

        try:
            counter = 0
            #update_time = time.time()
            #array = []
            while True:
                # read whats sent to this process and do stuff with it
                content = self.dump_queue()

                for i in content:
                    i:simple_packet
                    counter -= i.content

                v = random.random()/2 # *4 # 1,5
                #now = time.time()

                #update_time = now
                # send a debuff to another process
                if random.randint(0,1):
                    self.put_in_queue(random.randint(1,2), targets=(random.randint(0,15), ))
            

                self.put_in_queue([counter,v])
                #array = []
                counter += 1
                if counter >= 16:
                    raise KeyboardInterrupt
                time.sleep(v)

        except KeyboardInterrupt as e:
            #print(f"exiting id: {self.uid}")
            pass

        finally:
            self.safe_exit()