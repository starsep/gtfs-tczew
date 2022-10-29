from abc import ABC, abstractmethod
from zipfile import ZipFile

from configuration import outputGTFS


class GTFSGenerator(ABC):
    @abstractmethod
    def agencyInfo(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def stopsString(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def routesString(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def tripsString(self) -> str:
        raise NotImplementedError

    def generate(self):
        with ZipFile(outputGTFS, "w") as zipOutput:
            zipOutput.writestr("agency.txt", self.agencyInfo())
            zipOutput.writestr("stops.txt", self.stopsString())
            zipOutput.writestr("routes.txt", self.routesString())
            zipOutput.writestr("trips.txt", self.tripsString())
