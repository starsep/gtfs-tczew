from abc import ABC, abstractmethod
from zipfile import ZipFile

from configuration import outputGTFS


class GTFSGenerator(ABC):
    @abstractmethod
    def agencyInfo(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def stops(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def routes(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def trips(self) -> str:
        raise NotImplementedError

    def generate(self):
        with ZipFile(outputGTFS, "w") as zipOutput:
            zipOutput.writestr("agency.txt", self.agencyInfo())
            zipOutput.writestr("stops.txt", self.stops())
            zipOutput.writestr("routes.txt", self.routes())
            zipOutput.writestr("trips.txt", self.trips())
