"""Launcher/runtime contract without processes, credentials or HTTP calls."""
import io
import json
from unittest.mock import patch

import pytest
from scripts import start_demo


@pytest.mark.parametrize('body,expected', [
    ({'status':'ok','synthetic':True,'runtime':'synthetic-demo','liveReady':False}, True),
    ({'status':'ok','synthetic':True,'runtime':'local-demo'}, False),
    ({'status':'ok','synthetic':False,'runtime':'synthetic-demo'}, False),
    ({'status':'error','synthetic':True,'runtime':'synthetic-demo'}, False),
    ({'status':'ok','synthetic':True}, False),
    ([], False),
])
def test_launcher_checks_current_runtime_contract(body, expected):
    with patch.object(start_demo.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(body).encode())) as opened:
        assert start_demo.healthy() is expected
        opened.assert_called_once_with('http://127.0.0.1:8100/api/health', timeout=1)


def test_unavailable_server_is_not_ready():
    with patch.object(start_demo.urllib.request, 'urlopen', side_effect=OSError):
        assert start_demo.healthy() is False
