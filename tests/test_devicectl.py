"""DevicectlDriver tests with a fake runner; they never touch a real phone."""

import json
import subprocess

import pytest

from homebound.drivers import DevicectlDriver, DriverError

UDID = "00000000-0000000000000000"


def device(tunnel="connected", devmode="enabled", ddi=True, pairing="paired"):
    return {
        "hardwareProperties": {"deviceType": "iPhone", "reality": "physical", "udid": UDID,
                               "marketingName": "iPhone 16", "productType": "iPhone17,3"},
        "deviceProperties": {"name": "iPhone", "osVersionNumber": "26.6.1",
                             "developerModeStatus": devmode, "ddiServicesAvailable": ddi},
        "connectionProperties": {"pairingState": pairing, "tunnelState": tunnel, "transportType": "wired"},
    }


class FakeRunner:
    def __init__(self, devices, fail_with=None):
        self.devices = devices
        self.fail_with = fail_with
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        out_path = cmd[cmd.index("--json-output") + 1]
        if "list" in cmd:
            payload, rc = {"result": {"devices": self.devices}}, 0
        elif self.fail_with:
            payload, rc = {"error": self.fail_with}, 1
        else:
            payload, rc = {"result": {}}, 0
        with open(out_path, "w") as f:
            json.dump(payload, f)
        return subprocess.CompletedProcess(cmd, rc, stdout="", stderr="")


def test_status_ready():
    st = DevicectlDriver(runner=FakeRunner([device()])).status()
    assert st.ready and st.connected and st.ios_version == "26.6.1" and st.udid == UDID
    assert all(c.ok for c in st.checks)


@pytest.mark.parametrize("kw,check,fix_word", [
    ({"tunnel": "unavailable"}, "Connection", "Plug"),
    ({"devmode": "disabled"}, "Developer Mode", "Privacy & Security"),
    ({"ddi": False}, "Developer Disk Image", "auto-mount"),
    ({"pairing": "unpaired"}, "Pairing", "Trust"),
])
def test_status_failures_have_fixes(kw, check, fix_word):
    st = DevicectlDriver(runner=FakeRunner([device(**kw)])).status()
    assert not st.ready
    bad = next(c for c in st.checks if c.name == check)
    assert not bad.ok and fix_word in bad.fix


def test_no_iphone():
    st = DevicectlDriver(runner=FakeRunner([])).status()
    assert not st.ready and "Plug" in st.checks[-1].fix


def test_set_uses_equals_form_for_negative_longitude():
    runner = FakeRunner([device()])
    DevicectlDriver(runner=runner).set(34.07161, -118.44219)
    cmd = runner.calls[-1]
    assert "coordinate" in cmd and "--longitude=-118.442190" in cmd and "--latitude=34.071610" in cmd


def test_set_refuses_when_not_ready():
    with pytest.raises(DriverError) as e:
        DevicectlDriver(runner=FakeRunner([device(tunnel="unavailable")])).set(34.0, -118.0)
    assert "Plug" in e.value.fix


def test_invalid_coordinate():
    with pytest.raises(DriverError):
        DevicectlDriver(runner=FakeRunner([device()])).set(134.0, -118.0)


def test_unreachable_error_is_explained():
    err = {"code": 4016, "userInfo": {"NSLocalizedDescription": {
        "string": "The device is not able to fulfill the requested usage assertion requirements."}}}
    with pytest.raises(DriverError) as e:
        DevicectlDriver(runner=FakeRunner([device()], fail_with=err)).clear()
    assert "isn't reachable" in e.value.message and "Plug" in e.value.fix
