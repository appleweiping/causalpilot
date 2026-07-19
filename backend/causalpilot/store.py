"""Small in-memory repository for local demo missions."""

from __future__ import annotations

from threading import RLock

from .engine import MissionRuntime
from .schemas import StartMissionRequest


class MissionNotFound(KeyError):
    pass


class MissionStore:
    def __init__(self) -> None:
        self._missions: dict[str, MissionRuntime] = {}
        self._lock = RLock()

    def create(self, config: StartMissionRequest) -> MissionRuntime:
        mission = MissionRuntime(config)
        with self._lock:
            self._missions[mission.mission_id] = mission
        return mission

    def get(self, mission_id: str) -> MissionRuntime:
        with self._lock:
            mission = self._missions.get(mission_id)
        if mission is None:
            raise MissionNotFound(mission_id)
        return mission

    def reset(self, mission_id: str) -> MissionRuntime:
        previous = self.get(mission_id)
        mission = MissionRuntime(previous.config, parent_mission_id=mission_id)
        with self._lock:
            self._missions[mission.mission_id] = mission
        return mission

    def clear(self) -> None:
        with self._lock:
            self._missions.clear()


store = MissionStore()
