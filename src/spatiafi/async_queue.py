"""
Functions to create an efficient asynchronous queue, for making many requests to the SpatiaFI API.
"""

import asyncio
import logging
import multiprocessing as mp
import time
from asyncio import Task
from typing import Any, Callable, Dict, Optional

from google.api_core import retry_async
from httpx import HTTPStatusError

from spatiafi.session import get_async_session

logger = logging.getLogger(__name__)


def worker(
    queue, task_function, max_in_flight=1000, print_progress=100, start_time=None
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create client
    session = loop.run_until_complete(get_async_session())

    # Create results store
    results = {}

    def on_error(exc):
        # print(type(exc), "Retrying", flush=True)
        pass

    # Create a wrapper that awaits the task_function, retries on network exceptions,
    # and stores the result.  Stops the event loop if an exception is raised.
    async def wrapped_task(task_number, task_arg):
        try:
            response = await retry_async.AsyncRetry(
                predicate=AsyncQueue._retry_predicate,
                maximum=5,
                timeout=600,
                on_error=on_error,
            )(task_function)(task_arg, session=session)
            results[task_number] = response

            if (
                print_progress > 0
                and task_number > 0
                and task_number % print_progress == 0
            ):
                print(f"Finished task {task_number}", flush=True)

        except asyncio.exceptions.CancelledError:
            # We can ignore this exception.  It is raised when the task is cancelled.
            pass

        except Exception as e:
            print(
                f"Exception running task number {task_number} with arg: {task_arg}",
                flush=True,
            )
            print(type(e), "Not retrying anymore!", flush=True)
            raise e

    async def main():
        background_tasks = set()
        err = None

        def task_callback(task: Task):
            nonlocal err
            if task.exception() is not None:
                # Cancel all tasks
                for remaining_task in background_tasks:
                    remaining_task.cancel()
                err = task.exception()
            else:
                # To prevent keeping references to finished tasks forever,
                # make each task remove its own reference from the set after
                # completion.
                background_tasks.discard(task)

        while True:
            if err is not None:
                break

            # get a work_item from the queue
            # work_item is a tuple of (task_number, task) so that we can return the results in order
            work_item = queue.get()
            # print(f"Got work_item {work_item}", flush=True)

            # If work_item is None, then we wait for all tasks to finish and then break
            if work_item is None:
                print(
                    f"Waiting for {len(background_tasks)} async tasks to finish in subprocess"
                    + f": {time.time() - start_time}s"
                    if start_time is not None
                    else "",
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

            task.add_done_callback(task_callback)

            # This is a do-nothing call that allows background_tasks to run tasks while we continue to
            # iterate over the queue and add more tasks
            await asyncio.sleep(0.0)

            # Wait for len(background_tasks) to be less than max_in_flight before continuing the loop
            while len(background_tasks) > max_in_flight:
                await asyncio.sleep(0.1)

        if err is not None:
            raise err

    # Start the event loop and run the main function until it is finished
    loop.run_until_complete(main())

    # main is finished.  Close the session and the event loop.
    loop.close()

    # Put the results into the queue. At this point, the queue should be empty.
    assert queue.empty()
    queue.put(results)


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
        n_cores: Optional[int] = None,
        max_in_flight: Optional[int] = None,
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
            n_cores: The number of cores to use for multiprocessing.
            max_in_flight: The maximum number of tasks to run at once. This is roughly equivalent to the number of
                concurrent requests that will be made.
            max_queue_size: The maximum number of tasks to hold in the queue.  If the queue is full, the main function
                calling enqueue will block until there is space in the queue.
            print_progress: Print a message every `print_progress` tasks (roughly).  Set to 0 to disable printing.
                Note that this will print from multiple processes, so the messages may be interleaved.
        """

        if n_cores is None:
            n_cores = mp.cpu_count()
        if max_in_flight is None:
            max_in_flight = n_cores * 90

        # ensure print_progress is an int and is positive
        if type(print_progress) is not int:
            raise ValueError("print_progress must be an int")
        if print_progress < 0:
            raise ValueError("print_progress must be positive")

        self.task_function = task_function
        self.n_cores = n_cores
        self.max_in_flight = max_in_flight
        self.max_queue_size = max_queue_size
        self.print_progress = print_progress

        self._running = False
        self._start_time = None
        self._queue = None
        self._worker_process = None
        self._results = {}
        self._task_count = 0

    @staticmethod
    def _retry_predicate(exc):
        if isinstance(exc, HTTPStatusError) and (exc.response.status_code < 500):
            # 4xx is a valid response, so don't retry
            return False
        # Retry on all other exceptions
        return True

    def start(self):
        """Start the multiprocessing worker process."""
        self._start_time = time.time()

        # Create the queue and worker process
        self._queue = [
            mp.Manager().Queue(maxsize=self.max_queue_size) for _ in range(self.n_cores)
        ]
        self._worker_process = [
            mp.Process(
                target=worker,
                kwargs={
                    "queue": queue,
                    "task_function": self.task_function,
                    "max_in_flight": self.max_in_flight // self.n_cores,
                    "print_progress": self.print_progress,
                    "start_time": self._start_time,
                },
            )
            for queue in self._queue
        ]

        # Start the worker process
        [worker_process.start() for worker_process in self._worker_process]
        self._running = True

        print(
            f"Subprocesses and async loop started: {time.time() - self._start_time}s",
            flush=True,
        )

    def stop(self):
        """Stop the worker task."""
        if not self._running:
            return

        # Put None into the queue to signal that we are done
        [queue.put(None) for queue in self._queue]

        # Wait for the worker process to finish
        [worker_process.join() for worker_process in self._worker_process]

        print(
            f"Subprocess and {self._task_count} async tasks finished: {time.time() - self._start_time}s",
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

    @property
    def results(self):
        """
        Get the results from the worker task.

        This should be called after the worker task has been stopped.
        """
        if not self._results:
            self.stop()
            self._results = {}
            for queue in self._queue:
                # get results from queue
                results = queue.get()
                # merge results into self._results
                self._results.update(results)
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
        # Put the work_item into a queue
        queue = self._queue[self._task_count % self.n_cores]
        queue.put(work_item)
        self._task_count += 1
