import pytest
import requests
from spatiafi.session import get_session


def test_get_sync_session():
    session = get_session()

    # https://api.spatiafi.com/api/timeseries/point/-4.8759617382590985,59.015777063423926?coll_id=spatiafi-sea-level-rise-projections-global-v1.0-intlow

    lon, lat = -4.8759617382590985, 59.015777063423926
    coll_id = "spatiafi-sea-level-rise-projections-global-v1.0-intlow"
    url = "https://api.spatiafi.com/api/timeseries/point/" + str(lon) + "," + str(lat)

    query = {"coll_id": coll_id}

    r = session.get(url, params=query)

    assert r.status_code == 200


def test_get_sync_session__with_proxy():
    proxies = {
        "http": "http://fake-proxy.example.com:443",
        "https": "http://fake-proxy.example.com:443",
    }

    with pytest.raises(
        requests.exceptions.ProxyError,
        match="Failed to resolve 'fake-proxy.example.com'",
    ):
        get_session(proxies=proxies)
