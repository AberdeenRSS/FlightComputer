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

    def __init__(self, my_send_queue:multiprocessing.Queue, my_recv_queue:multiprocessing.Queue, process_uid_generator:uid_generator, uid) -> None:
        super().__init__()
        
        self.uid = uid

        self._process_uid_generator = process_uid_generator # uid total currently
        self._my_send_queue = my_send_queue
        self._my_recv_queue = my_recv_queue
    

    def get_from_queue(self) -> simple_packet | None:
        """
        Read whats sent to the process and dump it into an array
        """
        try:
            # drain the queue
            return self._my_recv_queue.get(block=False)
        except queue.Empty as e:
            return None
    

    def put_in_queue(self, contents, targets=(), target_type=[]) -> bool:
        """
        puts items into the queue for the main loop to read
        """
        p_uid_n = self._process_uid_generator.generate()
        p = simple_packet(p_uid_n, self.uid, contents, targets=targets, target_type=target_type)
        self._my_send_queue.put(p, block=False)


    def safe_exit(self):
        """
        close queues and exit
        """
        self._my_send_queue.close()
        self._my_recv_queue.close()



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
                q_content = self.get_from_queue()
                if q_content is not None:

                        counter -= q_content.content

                v = random.random()/2 # *4 # 1,5
                #now = time.time()

                #update_time = now
                # send a debuff to another process
                if random.randint(0,1):
                    self.put_in_queue(random.randint(1,2), targets=(1, random.randint(0,15) ))
            

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
