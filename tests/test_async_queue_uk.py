import asyncio
import json
import random

import pandas as pd

from spatiafi.async_queue import AsyncQueue
from spatiafi.session import get_async_session


async def get_point(row, session=None):
    if session is None:
        session = await get_async_session()

    # Create the url.  Note that this assumes that the series/dict has indices "lat" and "lon".
    url = (
        "https://api.spatiafi.com/api/timeseries/point/"
        + str(row["lon"])
        + ","
        + str(row["lat"])
    )

    query = {"coll_id": row["collection_id"]}

    r = await session.get(url, params=query)

    # raise for all errors except 2xx or 4xx:
    if not (200 <= r.status_code < 300 or 400 <= r.status_code < 500):
        r.raise_for_status()

    result = {row["collection_id"]: r.json()}
    return result


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
    coordinates = generate_random_coordinates(100)

    # Create a DataFrame
    df = pd.DataFrame(coordinates, columns=["lat", "lon"])

    collection_ids = [
        "spatiafi-extreme-wind-risk-static-global-v1.0",
        "spatiafi-sea-level-rise-projections-global-v1.0-int",
        "spatiafi-sea-level-rise-projections-global-v1.0-high",
        "spatiafi-extreme-precipitation-risk-projections-global-v1.0-ssp585",
        "spatiafi-extreme-wind-risk-projections-global-v1.0-ssp585",
        "spatiafi-extreme-cold-risk-projections-global-v1.0-ssp585",
        "uk-bgs-shrink-swell-open-data-ukcp09",
        "spatiafi-drought-risk-projections-global-v1.0-ssp245",
        "spatiafi-fluvial-flood-risk-historical-global-v1.0",
        "spatiafi-extreme-precipitation-risk-static-global-v1.0",
        "spatiafi-sea-level-rise-projections-global-v1.0-inthigh",
        "spatiafi-wildfire-risk-static-global-v1.0",
        "spatiafi-extreme-precipitation-risk-projections-global-v1.0-ssp245",
        "spatiafi-extreme-heat-risk-static-global-v1.0",
        "spatiafi-sea-level-rise-projections-global-v1.0-intlow",
        "uk-bgs-shrink-swell-open-data-ukcp18",
        "spatiafi-drought-risk-projections-global-v1.0-ssp585",
        "spatiafi-extreme-heat-risk-projections-global-v1.0-ssp245",
        "spatiafi-extreme-wind-risk-projections-global-v1.0-ssp245",
        "spatiafi-extreme-heat-risk-projections-global-v1.0-ssp585",
        "spatiafi-extreme-cold-risk-static-global-v1.0",
        "spatiafi-extreme-cold-risk-projections-global-v1.0-ssp245",
        "spatiafi-sea-level-rise-projections-global-v1.0-low",
    ]  # ,'spatiafi-drought-risk-static-global-v1.0', 'fathom-uk-v3.0-risk-category-historical','fathom-uk-v3.0-risk-category-ssp245', 'fathom-uk-v3.0-risk-category-ssp585']
    print(f"collection_ids length: {len(collection_ids)}")

    df["collection_id"] = [collection_ids for _ in df.index]
    df = df.explode("collection_id", ignore_index=True)

    print(f"df length: {df.shape[0]}")
    print(f"df:\n {df}")

    # Test the task function
    # https://api.spatiafi.com/api/timeseries/point/-4.8759617382590985,59.015777063423926?coll_id=spatiafi-sea-level-rise-projections-global-v1.0-intlow
    row = {
        "lat": 59.015777063423926,
        "lon": -4.8759617382590985,
        "collection_id": "spatiafi-sea-level-rise-projections-global-v1.0-intlow",
    }
    result = asyncio.run(get_point(row))

    print(f"Ran task_function with result:\n {result}")

    # Create an AsyncQueue
    with AsyncQueue(get_point) as async_queue:
        # Enqueue the tasks from the DataFrame
        [async_queue.enqueue(row) for _, row in df.iterrows()]

    # Get the results
    results = async_queue.results

    print(f"Got {len(results)} results")
    print("First 10 results:")
    print(results[:10])

    print("Storing results to file")
    with open("results.json", "w") as f:
        json.dump(results, f)

    print("Done")


if __name__ == "__main__":
    test_async_queue_with_uk_points()
