from causalpilot.store import store


def pytest_runtest_setup():
    store.clear()
