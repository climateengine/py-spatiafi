"""
Functions to create an efficient asynchronous queue, for making many requests to the SpatiaFI API.
"""

import asyncio
import logging
import multiprocessing as mp
import time
from typing import Any, Callable, Dict

from google.api_core import retry_async
from httpx import HTTPStatusError, RequestError

from spatiafi.session import get_async_session

logger = logging.getLogger(__name__)


class AsyncQueue:
    """
    An efficient asynchronous worker queue, for making many requests to the SpatiaFI API.

    A multiprocessing process is used to run an asyncio event loop to asynchronously make requests.
    This allows us to use many CPU cores to make requests, each running a separate process and event loop.

    This queue is designed to be used with the `with` statement. Entering the `with` statement will start the
    subprocess and event loop.  Exiting the `with` statement will wait for all tasks to finish and then stop the
    event loop and subprocess.

    In addition to managing the event loop and multiprocessing process, a wrapper is provided to run the task
    function.  This wrapper will catch network exceptions and retry the task function.  If an exception is raised,
    the event loop will be stopped and the exception will be raised.

    Example usage:
        with AsyncQueue(task_function) as async_queue:
            [async_queue.enqueue(row) for _, row in df.iterrows()]
        results = async_queue.results

    For a complete example see tests/test_async_queue.py
    """

    def __init__(
        self,
        task_function: Callable[[Dict[str, Any]], Any],
        max_queue_size: int = 1000,
        print_progress: int = 100,
    ):
        """
        Create an AsyncQueue.

        A valid task_function must:
          * Be an async function
          * Take a single argument
          * Take an optional session argument (if not provided, an async session will be created)
          * Return a single, serializable object

        Args:
            task_function: An async function that takes a single argument and returns a single, serializable object.
            max_queue_size: The maximum number of tasks to queue.  If the queue is full, the main process will block
                until there is space in the queue.
            print_progress: Print a message every `print_progress` tasks (roughly).  Set to 0 to disable printing.
        """
        self.task_function = task_function
        self.max_queue_size = max_queue_size

        # ensure print_progress is an int and is positive
        if type(print_progress) is not int:
            raise ValueError("print_progress must be an int")
        if print_progress < 0:
            raise ValueError("print_progress must be positive")

        self.print_progress = print_progress

        self._running = False
        self._start_time = None
        self._queue = None
        self._worker_process = None
        self._results = {}
        self._task_count = 0

    @staticmethod
    def _retry_predicate(exc):
        if isinstance(exc, RequestError):
            return True
        if isinstance(exc, HTTPStatusError) and exc.response.status_code == 429:
            return True
        return False

    def _get_worker(self):
        """
        Get a worker process.

        This is a generator that yields a worker process.
        """

        def worker(queue):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create client
            session = loop.run_until_complete(get_async_session())

            # Create results store
            results = {}

            # Create a wrapper that awaits the task_function, retries on network exceptions,
            # and stores the result.  Stops the event loop if an exception is raised.
            async def wrapped_task(task_number, task_arg):
                try:
                    response = await retry_async.AsyncRetry(
                        predicate=AsyncQueue._retry_predicate, timeout=None
                    )(self.task_function)(task_arg, session=session)
                    results[task_number] = response

                    if (
                        self.print_progress > 0
                        and task_number > 0
                        and task_number % self.print_progress == 0
                    ):
                        print(f"Finished task {task_number}", flush=True)

                except Exception as e:
                    loop.stop()
                    print(e, flush=True)
                    raise e

            async def main():
                background_tasks = set()

                while True:
                    # get a work_item from the queue
                    # work_item is a tuple of (task_number, task) so that we can return the results in order
                    work_item = queue.get()
                    # print(f"Got work_item {work_item}", flush=True)

                    # If work_item is None, then we wait for all tasks to finish and then break
                    if work_item is None:
                        print(
                            f"Waiting for {len(background_tasks)} async tasks to finish in subprocess: "
                            f"{time.time() - self._start_time}s",
                            flush=True,
                        )
                        await asyncio.gather(*background_tasks)
                        break  # break out of the while True loop

                    # Create an asyncio task from the work_item
                    task = asyncio.create_task(wrapped_task(*work_item))

                    # Add task to the set.
                    # Note: This creates a strong reference. Without this, we risk the garbage collector
                    # destroying the task
                    background_tasks.add(task)

                    # To prevent keeping references to finished tasks forever,
                    # make each task remove its own reference from the set after
                    # completion.
                    task.add_done_callback(background_tasks.discard)

                    # This is a do-nothing call that allows background_tasks to run tasks while we continue to
                    # iterate over the queue and add more tasks
                    await asyncio.sleep(0.0)

            # Start the event loop and run the main function until it is finished
            loop.run_until_complete(main())

            # main is finished.  Close the session and the event loop.
            loop.close()

            # Put the results into the queue. At this point, the queue should be empty.
            assert queue.empty()
            queue.put(results)

        return worker

    def start(self):
        """Start the multiprocessing worker process."""
        self._start_time = time.time()

        # Create the queue and worker process
        self._queue = mp.Manager().Queue(maxsize=self.max_queue_size)
        self._worker_process = mp.Process(
            target=self._get_worker(), args=(self._queue,)
        )

        # Start the worker process
        self._worker_process.start()
        self._running = True

        print(
            f"Subprocess and async loop started: {time.time() - self._start_time}s",
            flush=True,
        )

    def stop(self):
        """Stop the worker task."""
        if not self._running:
            return

        # Put None into the queue to signal that we are done
        self._queue.put(None)

        # Wait for the worker process to finish
        self._worker_process.join()

        print(
            f"Subprocess and async tasks finished: {time.time() - self._start_time}s",
            flush=True,
        )
        self._running = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        # If an exception was raised, let it propagate
        if exc_type is not None:
            return False

    def __del__(self):
        self.stop()

    @property
    def results(self):
        """
        Get the results from the worker task.

        This should be called after the worker task has been stopped.
        """
        if not self._results:
            self.stop()
            self._results = self._queue.get()
            # results is a dict. return a list of values, sorted by key (task_number)
            self._results = [self._results[key] for key in sorted(self._results.keys())]
        return self._results

    def enqueue(self, arg):
        """
        Enqueue a task.
        """

        if not self._running:
            raise RuntimeError("AsyncQueue is not running")

        work_item = (self._task_count, arg)
        self._queue.put(work_item)
        self._task_count += 1
