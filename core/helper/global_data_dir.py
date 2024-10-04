from datetime import UTC, datetime


global user_data_dir
user_data_dir = ''

def set_user_data_dir(dir: str):
    global user_data_dir
    user_data_dir = dir

def get_user_data_dir():
    global user_data_dir
    return user_data_dir

cur_flight_dir = ''

def reset_flight_data_dir():
    global cur_flight_dir
    
    cur_flight_dir = ''

def get_cur_flight_data_dir():
    global cur_flight_dir
    
    if cur_flight_dir == '':
        date_file_safe = datetime.now(UTC).isoformat().replace('-', '_').replace(':', '_').replace('.', '_')
        cur_flight_dir = f'{get_user_data_dir()}/flight_at_{date_file_safe}'
    
    return cur_flight_dir
