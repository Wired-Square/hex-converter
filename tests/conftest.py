import importlib
import pytest

@pytest.fixture(scope="session")
def logic():
    return importlib.import_module("hex_converter.logic")
