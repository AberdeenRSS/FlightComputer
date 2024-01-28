import asyncio
import datetime
import traceback
import kivy
from pathlib import Path

from app.helper.global_data_dir import set_user_data_dir
kivy.require('2.1.0') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.scatterlayout import ScatterLayout
from kivy.metrics import cm
from kivy.core.window import Window
from kivy.logger import Logger, LOG_LEVELS
from kivy.utils import platform
from kivy.config import Config
import os
import logging

# We need a reference to the Java activity running the current
# application, this reference is stored automatically by
# Kivy's PythonActivity bootstrap

class CrashScreen(App):
    error: str

    def __init__(self, error, **kwargs):
        self.error = error
        super().__init__(**kwargs)

    def build(self):
        exception_label = Label(text=f'Uncaught exception, the app crashed with the following message:\n {self.error}',  shorten=False, font_size=16, valign='center' )
        exception_label.size = exception_label.texture_size

        layout = ScatterLayout()
        layout.add_widget(exception_label)

        return layout


async def main():

    global user_data_dir

    logging.disable()

    # logging.basicConfig(level=logging.WARN)

    # logging.getLogger('httpx').setLevel(level=logging.WARN)
    # logging.getLogger('httpcore').setLevel(level=logging.WARN)
    # logging.getLogger('urllib3').setLevel(level=logging.WARN)
    # logging.getLogger('requests').setLevel(level=logging.WARN)

    # os.environ['KIVY_LOG_MODE'] = 'KIVY'

    Config.set('kivy', 'log_level', 'debug')
    Config.set('kivy', 'log_enable ', 1)
    # Config.set('kivy', 'log_dir ', 'logs')
    # Config.set('kivy', 'log_name', '%y-%m-%d_%_.txt')

    Logger.setLevel('DEBUG')


    # Do the import within the try block in case
    # there are problems with it. In that
    # case the crash screen can still be shown
    from app.init_app import init_app

    ui_app, worker_process = init_app()

    set_user_data_dir(ui_app.user_data_dir)

    # Call run first, so the build process
    # is complete, before the worker process is initialized
    ui_coroutine = ui_app.async_run()
    ui_task = asyncio.create_task(ui_coroutine)

    worker_task = asyncio.create_task(worker_process())

    # Wait for either the kivy app or the worker to complete/crash
    done, pending = await asyncio.wait([ui_task, worker_task], return_when=asyncio.FIRST_COMPLETED)

    # Stop the ui in case the worker crashed, so that we can create a new ui with the error
    if not ui_task.done():
        ui_app.stop()

    if not worker_task.done():
        worker_task.cancel()

    # Throw exceptions if any where produced
    for d in done:
        if d.exception() is None:
            continue
        e = d.exception()
        if e:
            raise e

if __name__ == '__main__':
    # Try running the app
    # If an exception occurs start a "Crash App" that just
    # shows the exception and stack trace
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except:
        CrashScreen(traceback.format_exc()).run()
        raise
