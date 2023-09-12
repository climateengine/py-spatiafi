"""
Tests for the AsyncQueue class.

Can also be used as an example of how to use AsyncQueue.

A valid AsyncQueue task must:
  * Be an async function
  * Take a single argument
  * Take an optional session argument (if not provided, an async session will be created)
  * Return a single, serializable object

If your task function requires multiple arguments, you can:
  * Use a wrapper function or closure (may not work on Windows or 'spawn' multiprocessing)
  * Create a new function using `functools.partial` (as shown here)
  * Pass a tuple as the argument and unpack it in the task function
    e.g. `async_queue.enqueue((arg1, arg2))` and `async def task_function(args): arg1, arg2 = args`

"""
import asyncio
import random
from functools import partial

import pandas as pd

from spatiafi.async_queue import AsyncQueue
from spatiafi.session import get_async_session


async def get_point(item_id, row, session=None):
    """
    Get a point from the SpatiaFI API.

    Note: This is *not* a valid task function for AsyncQueue, because it takes two arguments.
    """
    if session is None:
        session = await get_async_session()

    # Create the url.  Note that this assumes that the series/dict has indices "lat" and "lon".
    url = (
        "https://api.spatiafi.com/api/point/" + str(row["lon"]) + "," + str(row["lat"])
    )

    query = {"item_id": item_id}

    r = await session.get(url, params=query)

    # We want to raise for all errors except 400 (bad request)
    if not (r.status_code == 200 or r.status_code == 400):
        r.raise_for_status()

    return r.json()


# Create a partial function that only takes one argument
get_point_partial = partial(
    get_point, "ce-drought-risk-projections-global-v1.0-ssp245-long-term-2020"
)


# Helper function to generate random UK coordinates
def generate_random_coordinates(num_points=1):
    coordinates = []
    for _ in range(num_points):
        latitude = random.uniform(49.9, 59.5)
        longitude = random.uniform(-8.2, 1.8)
        coordinates.append((latitude, longitude))
    return coordinates


def test_async_queue_with_uk_points():
    # Generate 1000 random coordinates
    coordinates = generate_random_coordinates(1000000)

    # Create a DataFrame
    df = pd.DataFrame(coordinates, columns=["lat", "lon"])

    print(f"df:\n {df}")

    # Test the task function on the first row to make sure it works as expected
    row = df.iloc[0]
    result = asyncio.run(get_point_partial(row))

    print(f"Ran task_function on first row with result:\n {result}")

    # Create an AsyncQueue
    with AsyncQueue(get_point_partial) as async_queue:
        # Enqueue the tasks from the DataFrame
        [async_queue.enqueue(row) for _, row in df.iterrows()]

    # Get the results
    results = async_queue.results

    print(f"Got {len(results)} results")
    print("First 10 results:")
    print(results[:10])


if __name__ == "__main__":
    test_async_queue_with_uk_points()
