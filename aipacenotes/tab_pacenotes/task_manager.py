from concurrent.futures import ThreadPoolExecutor, TimeoutError

class TaskManager:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = []
    
    def get_future_count(self):
        return len(self.futures)
    
    def gc_finished(self):
        self.futures = [future for future in self.futures if not future.done()]

    def submit(self, fn, arg):
        print(f"submitting task with fn={fn} arg='{arg}'")
        future = self.executor.submit(fn, arg)
        future.add_done_callback(self.handle_future)
        self.futures.append(future)

    def handle_future(self, future):
        try:
            # If the job has completed and raised an exception, this
            # will re-raise the exception. If the job has not yet completed,
            # this will raise a concurrent.futures.TimeoutError.
            future.result(timeout=0)
        except TimeoutError:
            pass
        except Exception as e:
            import traceback
            print(f"An error occurred in a future: {e}")
            traceback.print_exc()

    def shutdown(self):
        self.wait_for_futures()
        self.executor.shutdown()

    def wait_for_futures(self):
        return [future.result() for future in self.futures]
