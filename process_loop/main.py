import multiprocessing
import time
import queue
import importlib

from bases.packet import base_packet, simple_packet
from bases.process import base_process
from generators.packet_uid_generator import uid_generator

# only import whats needed, all sub-process can import their own things

# ---
# Hard cap of processes = 16
total_processes = 16 # dont change this unless you know what you're doing
# The total of which "active processes" are true
active_processes = 16

# RECOMMENDED


# which processes are active?
active_processes_list = [
    True,  # 0
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
# validate if  active processes is correct
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

# ensure nothing bad happens due to a mistake, crash out if this
if total_processes < active_processes:
    raise ValueError("total_processes cannot be less than active processes")

# check if array length (active_processes_list) is the same as total_processes
if total_processes != len(active_processes_list):
    raise ValueError("Total processes is not the sameas active processes list")

# initial clean ups and pre-run stuff

# clean dump file
dump_file = "./dump.txt"
with open(dump_file, "w") as f:
    f.write("")
#


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
        try:
            mod = importlib.import_module(f"processes._{i}.setup")
            base_proc = mod.custom_process(s, r, process_uid_generator, i)
        except ImportError as e:
            base_proc = base_process(s, r, process_uid_generator, i)
        process_array[i] = (s, r, base_proc)

    return process_array


def queue_main(process_array, process_uid_generator:uid_generator):
    """
    Main loop
    """
    process_array:list[tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]]
    running_totals_two = [0] * total_processes
    count = 0
    old_val = 0
    all_packets = []
    iteration = 0
    mean_cycle_time = 0
    cycle_time_list = [0]*100

    for i in range(0, total_processes):
        if not active_processes_list[i]:
            # check if its supposed to be active
            continue
        process_array[i][2].start()

    waiting = True
    alt_mode = False
    ready_list = []
    print("main listening")
    while waiting:
        for i in range(0, total_processes):
            if not active_processes_list[i]:
                continue
            
            if alt_mode:
                print(f"sent go to {i}")
                process_array[i][1].put("go", block=False)
                continue
            try:
                tmp = process_array[i][0].get(block=False)
                if tmp.content == "ready":
                    print(f"{i} is ready")
                    all_packets.append(tmp)
                    ready_list.append(i)
            except queue.Empty:
                pass
        
        if len(ready_list) == active_processes:
            if alt_mode:
                waiting = False
            alt_mode = True

    print("Moving to main loop")

    while True:
        # loop through fast
        cycle_start_time = empty_time = time.time()
        for i in range(0, total_processes):
            # loop through all processes & check if the queue is empty, if it isnt empty it and log that
            
            # description of following variable
            # process_array[i] = tuple[multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Process, int]
            process_array[i]
            
            # if i not in active process list, skip to next iteration
            if not active_processes_list[i]:
                continue

            try:
                # get from the queue
                selected_packet:simple_packet = process_array[i][0].get(block=False)
                # check if its a packet, else skip it
                if not isinstance(selected_packet, base_packet):
                    print("Dropping packet: Not a packet")
                    continue

                # try to identify and send to targets, packets are dropped if this is bad or empty, but still logged
                try:
                    # check if the length is greater than 0 (not [] <- default)
                    if len(selected_packet.targets) > 0:
                        # try to loop through them
                        for j in selected_packet.targets:
                            # check if j is an int and if its within the right range
                            if j >= 0 and j <= 16:
                                # check its targetting a running process
                                if active_processes_list[j]:
                                    # put it into the processes queue
                                    process_array[j][1].put(selected_packet, block=False)
                        
                # if somethings goes wrong, specifically a type error:
                except TypeError as e:
                    selected_packet.failed = 1
                    raise TypeError("Dropping packet: Targets must be an iterable")

                try: 
                    # temp testing stuff
                    running_totals_two[selected_packet.sender_uid] = selected_packet.content[0]
                except:
                    continue

                # append it to a list of all packets
                all_packets.append(selected_packet)

            except queue.Empty as e:
                # empty cycle, nothing happened
                pass
        
        empty_time = time.time() - empty_time
        # save amount of time it takes to empty

        for i in range(0, len(running_totals_two)):
            if running_totals_two[i] != "/" and i != 1 and int(running_totals_two[i]) >= 15:
                running_totals_two[i] = "/"
                count += 1

        val = int(time.time())
        val = val%10
        if val != old_val:
            # every second output stuff for us to read
            old_val = val
            print(empty_time)
            print(running_totals_two)
            print(process_uid_generator.get_current_uid())
            for i in range(0, active_processes):
                if active_processes_list[i]:
                    if not process_array[i][2].is_alive():
                        print(f"{i} is dead")
                        active_processes_list[i] = False
            print(f"cycle: {iteration}, time: {mean_cycle_time}")
            print(f"{time.time()-begin} --- \n")

            if count >= active_processes-1 and not process_array[1][2].is_alive():
                for packet in all_packets:
                    packet:simple_packet
                    with open(dump_file, "a") as f:

                        f.write(f"{packet.failed}, {packet.uid}, {packet.sender_uid}, {packet.targets}, {packet.content}\n")

                break
        

        iteration += 1
        # avoid this running at iteration 0
        if iteration%100 == 0:
            pass
        cycle_time_list[iteration%100] = time.time() - cycle_start_time
        mean_cycle_time = sum(cycle_time_list) / len(cycle_time_list)


        


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