import sys
from dataclasses import dataclass
from typing import List, Dict

import httpx
import overpy

from configuration import (
    OPENSTREETMAP_DOMAIN,
    TCZEW_PUBLIC_TRANSPORT_RELATION_ID,
    OVERPASS_URL,
    cache,
)
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


class OSM:
    def __init__(self) -> None:
        super().__init__()
        self.api = overpy.Overpass(url=OVERPASS_URL)
        self.overpassRelations = dict()
        self.overpassWays = dict()
        self.overpassNodes = dict()
        self.mainRelation: Relation = None

    def parseElement(self, elementId: int, elementType: str) -> Element:
        if elementType == "relation":
            return self.parseRelation(elementId)
        if elementType == "way":
            return self.parseWay(elementId)
        if elementType == "node":
            return self.parseNode(elementId)

    def parseWay(self, wayId: int) -> Way:
        way = self._getWay(wayId)
        return Way(
            type=way["type"],
            id=way["id"],
            tags=way["tags"],
            nodes=[self.parseNode(nodeId=nodeId) for nodeId in way["nodes"]],
        )

    @cache.memoize()
    def _getWay(self, wayId: int):
        url = f"{OPENSTREETMAP_API}/way/{wayId}.json"
        return httpx.get(url).json()["elements"][0]

    def parseNode(self, nodeId: int) -> Node:
        node = self._getNode(nodeId)
        return Node(
            type=node["type"],
            id=node["id"],
            tags=node["tags"] if "tags" in node else dict(),
            lat=node["lat"],
            lon=node["lon"],
        )

    @cache.memoize()
    def _getNode(self, nodeId: int):
        url = f"{OPENSTREETMAP_API}/node/{nodeId}.json"
        return httpx.get(url).json()["elements"][0]

    def parseRelation(self, relationId: int) -> Relation:
        relation = self._getRelation(relationId)
        return Relation(
            type=relation["type"],
            id=relation["id"],
            members=[
                RelationMember(
                    type=member["type"],
                    ref=member["ref"],
                    role=member["role"],
                    element=self.parseElement(
                        elementId=member["ref"], elementType=member["type"]
                    ),
                )
                for member in relation["members"]
            ],
            tags=relation["tags"],
        )

    @cache.memoize()
    def _getRelation(self, relationId: int):
        url = f"{OPENSTREETMAP_API}/relation/{relationId}.json"
        return httpx.get(url).json()["elements"][0]

    @cache.memoize()
    def _getRelationFromOverpass(self, relationId: int):
        query = f"""
        [out:json][timeout:250];
        relation(id:{relationId});
        (._;>>;);
        out body;
        """
        return self.api.query(query)

    def _saveRelationDataFromOverpass(self, relationId: int):
        overpassResult = self._getRelationFromOverpass(relationId)
        for relation in overpassResult.relations:
            self.overpassRelations[relation.id] = relation
        for way in overpassResult.ways:
            self.overpassWays[way.id] = way
        for node in overpassResult.nodes:
            self.overpassNodes[node.id] = node

    def parseElementFromOverpass(self, elementType, elementId):
        if elementType == "relation":
            return self.parseRelationFromOverpass(elementId)
        if elementType == "way":
            return self.parseWayFromOverpass(elementId)
        if elementType == "node":
            return self.parseNodeFromOverpass(elementId)

    def parseNodeFromOverpass(self, nodeId: int) -> Node:
        node = self.overpassNodes[nodeId]

        return Node(
            id=node.id,
            type="node",
            lat=node.lat,
            lon=node.lon,
            tags=node.tags,
        )

    def parseWayFromOverpass(self, wayId: int) -> Way:
        way = self.overpassWays[wayId]

        return Way(
            id=way.id,
            type="way",
            tags=way.tags,
            nodes=[self.parseNodeFromOverpass(node.id) for node in way.nodes],
        )

    def parseRelationFromOverpass(self, relationId: int) -> Relation:
        relation = self.overpassRelations[relationId]

        def overpyType(relationMember) -> str:
            t = type(relationMember)
            if t == overpy.RelationRelation:
                return "relation"
            if t == overpy.RelationWay:
                return "way"
            if t == overpy.RelationNode:
                return "node"
            raise Exception(f"Unsupported type: {t}")

        return Relation(
            id=relation.id,
            type="relation",
            tags=relation.tags,
            members=[
                RelationMember(
                    ref=member.ref,
                    type=overpyType(member),
                    role=member.role,
                    element=self.parseElementFromOverpass(
                        elementType=overpyType(member), elementId=member.ref
                    ),
                )
                for member in relation.members
            ],
        )

    def fetchMainRelation(self):
        # return self.parseRelation(relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID)
        self._saveRelationDataFromOverpass(
            relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID
        )
        self.mainRelation = self.parseRelationFromOverpass(
            relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID
        )

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

    def getRoutes(self) -> List[Relation]:
        return [
            member.element
            for member in self.mainRelation.members
            if member.element.tags.get("route_master") == "bus"
        ]
