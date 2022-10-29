from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict

from configuration import OPENSTREETMAP_DOMAIN
from log import printWarning

OPENSTREETMAP_API = f"{OPENSTREETMAP_DOMAIN}/api/0.6"


@dataclass(frozen=True, eq=True)
class Element:
    type: str
    id: int
    tags: Dict[str, str]


@dataclass(frozen=True, eq=True)
class RelationMember:
    type: str
    ref: int
    role: str
    element: Element


@dataclass(frozen=True, eq=True)
class Relation(Element):
    members: List[RelationMember]


@dataclass(frozen=True, eq=True)
class Node(Element):
    lat: float
    lon: float


@dataclass(frozen=True, eq=True)
class Way(Element):
    nodes: List[Node]


class OSMSource(ABC):
    mainRelation: Relation

    @abstractmethod
    def fetchRelation(self, relationId: int) -> Relation:
        raise NotImplementedError

    @abstractmethod
    def fetchWay(self, wayId: int) -> Way:
        raise NotImplementedError

    @abstractmethod
    def fetchNode(self, nodeId: int) -> Node:
        raise NotImplementedError

    def fetchElement(self, elementId: int, elementType: str) -> Element:
        if elementType == "relation":
            return self.fetchRelation(elementId)
        elif elementType == "way":
            return self.fetchWay(elementId)
        elif elementType == "node":
            return self.fetchNode(elementId)
        else:
            raise NotImplementedError(f"unknown element type: {elementType}")

    def savePublicTransportRelation(self, relationId: int):
        self.mainRelation = self.fetchRelation(relationId)

    def getRoutes(self) -> List[Relation]:
        return [
            member.element
            for member in self.mainRelation.members
            if member.element.tags.get("route_master") == "bus"
        ]

    def _getStops(self, element: Element) -> List[Element]:
        result = list()
        stopRefs = set()
        if element.tags.get("highway") == "bus_stop":
            if "ref" in element.tags:
                ref = element.tags["ref"]
                if ref not in stopRefs:
                    result.append(element)
                    stopRefs.add(ref)
            else:
                printWarning(f"Missing ref for {element}")
            result.append(element)
        if type(element) == Relation:
            for member in element.members:
                memberStops = self._getStops(member.element)
                for memberStop in memberStops:
                    ref = memberStop.tags["ref"]
                    if ref not in stopRefs:
                        result.append(memberStop)
                        stopRefs.add(ref)
        return result

    def getStops(self) -> Dict[int, Node]:
        result = dict()
        for stop in self._getStops(self.mainRelation):
            ref = stop.tags["ref"]
            if ";" in ref:
                for r in ref.split(";"):
                    result[int(r)] = stop
            else:
                result[int(ref)] = stop
        return result
