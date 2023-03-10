import asyncio
import traceback
import kivy
kivy.require('2.1.0') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window

# We need a reference to the Java activity running the current
# application, this reference is stored automatically by
# Kivy's PythonActivity bootstrap

class CrashScreen(App):
    error: str

    def __init__(self, error, **kwargs):
        self.error = error
        super().__init__(**kwargs)

    def build(self):
        return Label(text=f'Uncaught exception, the app crashed with the following message:\n {self.error}', text_size=Window.size, font_size=16, valign='center' )


async def main():

    # Do the import within the try block in case
    # there are problems with it. In that
    # case the crash screen can still be shown
    from app.init_app import init_app

    ui_app, worker_process = init_app()

    # Call run first, so the build process
    # is complete, before the worker process is initialized
    ui_coroutine = ui_app.async_run()
    ui_task = asyncio.create_task(ui_coroutine)

    # Wait for either the kivy app or the worker to complete/crash
    done, pending = await asyncio.wait([ui_task, worker_process()], return_when=asyncio.FIRST_COMPLETED)

    # Stop the ui in case the worker crashed, so that we can create a new ui with the error
    if not ui_task.done():
        ui_app.stop()

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
