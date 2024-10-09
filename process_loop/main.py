import multiprocessing
import time
import queue

from bases.packet import simple_packet
from bases.process import base_process
from generators.packet_uid_generator import uid_generator

# only import whats needed, all sub-process can import their own things

# ---
# Hard cap of processes = 16
total_processes = 16 # dont change this unless you know what you're doing
# The total of which "active processes" are true
active_processes = 15

# which processes are active?
active_processes_list = [
    False,  # 0
    True,  # 1
    True,  # 2
    True,  # 3
    True,  # 4
    True,  # 5
    True,  # 6
    True,  # 7
    True,  # 8
    True,  # 9
    True,  # 10
    True,  # 11
    True,  # 12
    True,  # 13
    True,  # 14
    True   # 15
]
# ---
count = 0
for i in active_processes_list:
    if i:
        count += 1

if count != active_processes:
    v = ""
    b= True
    while b: 
        v = input("Are you sure active_processes and active_processes_list are properly matched? (yes/no/Auto correct) y/N/a: ") or "n"
        if v.lower() == "y":
            b = False
        elif v.lower() == "a":
            print(f"updating from {active_processes} to {count}")
            active_processes = count
            b = False
        else:
            raise ValueError("Exiting due to value mismatch between active_processes and active_processes_list")

# ---
"""

The script starts below here

"""
# ---


def queue_setup(process_uid_generator:uid_generator):
    """
    Generate total_processes different processes
    """
    process_array:list[tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]] = [""]*total_processes
    for i in range(0,total_processes):
        if not active_processes_list[i]:
            # check if its supposed to be active
            continue
        s = multiprocessing.Queue()
        r = multiprocessing.Queue()
        base_proc = base_process(s, r, i, process_uid_generator)
        process_array[i] = (s, r, base_proc)

    for i in range(0, total_processes):
        if not active_processes_list[i]:
            # check if its supposed to be active
            continue
        process_array[i][2].start()

            

    return process_array


def queue_main(process_array, process_uid_generator:uid_generator):
    """
    Main loop
    """
    process_array:list[tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]]
    running_totals = [0] * total_processes
    running_totals_two = [0] * total_processes
    count = 0
    old_val = 0
    all_packets = []
    while True:
        # loop through fast
        empty_time = time.time()
        for i in range(0, total_processes):
            # loop through all processes & check if the queue is empty, if it isnt empty it and log that
            process_array[i]
            # process_array[i] = tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]
            
            # if i not in active process list, skip to next iteration
            if not active_processes_list[i]:
                continue

            try:
                # drain the queue
                temp:simple_packet = process_array[i][0].get(block=False)
                all_packets.append(temp)

                if len(temp.targets) > 0:
                    for j in temp.targets:
                        if active_processes_list[j]:
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
            print(process_uid_generator.get_current_uid())
            print(f"{time.time()-begin} --- \n")

            if count >= active_processes:
                for packet in all_packets:
                    packet:simple_packet
                    with open("./dump.txt", "a") as f:

                        f.write(f"{packet.uid}, {packet.sender_uid}, {packet.targets}, {packet.content}\n")

                break


if __name__ == '__main__':
    begin = time.time()
    #a = pipe_setup()
    v = uid_generator()
    a = queue_setup(v)
    try:
        #pipe_main(a)
        queue_main(a, v)
    except KeyboardInterrupt as e:
        print("Shutting down")
    finally:
        print("killing processes")
        for i in range(0, total_processes):
            if not active_processes_list[i]:
                # check if its supposed to be active
                continue
            a[i][0].close()
            a[i][1].close()
            a[i][2].terminate()
        
        print("done")