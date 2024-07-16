from datetime import datetime
from io import TextIOWrapper
import logging
from pathlib import Path
import time

from core.helper.global_data_dir import get_cur_flight_data_dir


class FileLogger(logging.Handler):

    current_file_handle: TextIOWrapper | None = None

    def __init__(self, level=logging.NOTSET):
        super(FileLogger, self).__init__(level=level)

        self.cur_flight_dir = Path(get_cur_flight_data_dir())
        self.folder_created = False
        self.last_file_created = time.time()
        self.current_file_count = 0
        self.max_file_age = 60*5

    def create_next_file_handle_if_required(self):

        if not self.folder_created:
            try:

                self.cur_flight_dir.mkdir(parents=True, exist_ok=True)

            except Exception as e:
                
                pass # We cannot log here as this is called from the logger

            self.folder_created = True

        self.open_new_file_if_required()

        
    def open_new_file_if_required(self):

        now = time.time() 
        since_last_log_file = (now - self.last_file_created)

        if self.current_file_handle is not None and  since_last_log_file < self.max_file_age:
            return
        
        if self.current_file_handle:
            try:
                self.current_file_handle.close()
            except:
                pass

        self.last_file_created = now
        self.current_file_count = self.current_file_count + 1

        path = Path(f'{self.cur_flight_dir.as_posix()}/log_{self.current_file_count}.txt')

        try:
            self.current_file_handle = path.open('a')
        except Exception as e:
            pass


    def emit(self, record):
        def f(dt=None):

            self.create_next_file_handle_if_required()

            if self.current_file_handle is None:
                return
            
            content = self.format(record)

            try:
                self.current_file_handle.write( f'{datetime.now().isoformat()}: {content}\n')
            except Exception as e:
                pass

        f()
        # Clock.schedule_once(f)

    def flush(self):
        if self.current_file_handle is None:
            return
        
        try:
            self.current_file_handle.flush()
        except:
            pass


