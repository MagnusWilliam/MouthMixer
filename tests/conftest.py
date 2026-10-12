import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A throwaway library folder for each test."""
    monkeypatch.setenv("MOUTHMIXER_HOME", str(tmp_path / "MouthMixer"))
    return tmp_path / "MouthMixer"
