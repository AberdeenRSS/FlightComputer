global user_data_dir
user_data_dir = ''

def set_user_data_dir(dir: str):
    global user_data_dir
    user_data_dir = dir

def get_user_data_dir():
    global user_data_dir
    return user_data_dir

    