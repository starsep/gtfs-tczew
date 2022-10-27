from dataclasses import dataclass
from typing import List, Dict

import httpx
import overpy
from diskcache import Cache

from configuration import OPENSTREETMAP_DOMAIN, TCZEW_PUBLIC_TRANSPORT_RELATION_ID, OVERPASS_URL

OPENSTREETMAP_API = f"{OPENSTREETMAP_DOMAIN}/api/0.6"

cache = Cache("cache")


@dataclass
class Element:
    type: str
    id: int
    tags: Dict[str, str]


@dataclass
class RelationMember:
    type: str
    ref: int
    role: str
    element: Element


@dataclass
class Relation(Element):
    members: List[RelationMember]


@dataclass
class Node(Element):
    lat: float
    lon: float


@dataclass
class Way(Element):
    nodes: List[Node]


class OSM:
    def __init__(self) -> None:
        super().__init__()
        self.api = overpy.Overpass(url=OVERPASS_URL)
        self.overpassRelations = dict()
        self.overpassWays = dict()
        self.overpassNodes = dict()

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

    def getMainRelation(self):
        # return self.parseRelation(relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID)
        self._saveRelationDataFromOverpass(
            relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID
        )
        return self.parseRelationFromOverpass(
            relationId=TCZEW_PUBLIC_TRANSPORT_RELATION_ID
        )
