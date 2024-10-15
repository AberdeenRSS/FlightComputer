
import queue
import random
import time

from bases.process import base_process
from generators.packet_uid_generator import uid_generator

from bases.packet import simple_packet

class custom_process(base_process):
    def __init__(self, my_send_queue: queue, my_recv_queue: queue, process_uid_generator:uid_generator, uid) -> None:
        # in file 2
        # therefore
        uid = 2
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
                q_content = self.get_from_queue()
                if q_content is not None:
                    if q_content.content != -50:
                        print(f"current {counter} adding {q_content.content} from packet id {q_content.uid}, sender: {q_content.sender_uid}, {self._my_recv_queue.qsize()} to go")
                        counter += q_content.content

                v = random.random()/2 # *4 # 1,5
                #now = time.time()

                #update_time = now
                # send a debuff to another process
                #if random.randint(0,1):
                #    self.put_in_queue(random.randint(1,2), targets=(random.randint(0,15), ))

                p_uid = self._process_uid_generator.generate()
                p = simple_packet(p_uid, self.uid, "a", "abc")
                self._my_send_queue.put_nowait(p)

                if random.randint(1,10) == 4:
                    self._my_send_queue.put_nowait("a")
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