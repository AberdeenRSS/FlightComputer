import multiprocessing
import time
import random
import queue

from bases.packet import base_packet, simple_packet
from bases.process import base_process, use_process_uid_number



def queue_setup(process_uid_number):
    """
    Generate 16 different processes
    """
    process_array:list[tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]] = []
    for i in range(0,16):
        s = multiprocessing.Queue()
        r = multiprocessing.Queue()
        base_proc = base_process(s, r, i, process_uid_number)
        process_array.append((s, r, base_proc))

    for i in process_array:
        i[2].start()

    return process_array


def queue_main(process_array, process_uid_number):
    """
    Main loop
    """
    process_array:list[tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]]
    running_totals = [0] *len(process_array)
    running_totals_two = [0] *len(process_array)
    count = 0
    end = len(process_array)
    old_val = 0
    all_packets = []
    while True:
        # loop through fast
        empty_time = time.time()
        for i in process_array:
            # loop through all processes & check if the queue is empty, if it isnt empty it and log that
            i:tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]
            try:
                # drain the queue
                temp:simple_packet = i[0].get(block=False)
                all_packets.append(temp)

                if len(temp.targets) > 0:
                    for j in temp.targets:
                        process_array[j][1].put(temp, block=False)
                    
                    continue
                running_totals_two[temp.sender_uid] = temp.content[0]

            except queue.Empty as e:
                pass
        
        empty_time = time.time() - empty_time
        # save amount of time it takes to empty

        for i in range(0, len(running_totals_two)):
            if running_totals_two[i] == 15:
                running_totals_two[i] = "/"
                count += 1
        val = int(time.time())
        val = val%10
        if val != old_val:
            # every second output stuff for us to read
            old_val = val
            print(empty_time)
            print(running_totals)
            print(running_totals_two)
            print(use_process_uid_number(process_uid_number, increment=False))
            print(f"{time.time()-begin} --- \n")

            if count >= end:
                for packet in all_packets:
                    packet:simple_packet
                    with open("./dump.txt", "a") as f:

                        f.write(f"{packet.uid}, {packet.sender_uid}, {packet.targets}, {packet.content}\n")

                break


if __name__ == '__main__':
    begin = time.time()
    #a = pipe_setup()
    v = multiprocessing.Value("i", 0)
    a = queue_setup(v)
    try:
        #pipe_main(a)
        queue_main(a, v)
    except KeyboardInterrupt as e:
        print("Shutting down")
    finally:
        print("killing processes")
        for i in a:
            i[0].close()
            i[1].close()
            i[2].terminate()
        
        print("done")