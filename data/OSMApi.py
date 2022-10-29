from abc import ABC

import httpx

from configuration import (
    OPENSTREETMAP_DOMAIN,
    cache,
)
from data.OSMSource import Way, Relation, RelationMember, Node, OSMSource

OPENSTREETMAP_API = f"{OPENSTREETMAP_DOMAIN}/api/0.6"


class OSMApi(OSMSource):
    def __init__(self, mainRelationId: int):
        super().__init__(mainRelationId)

    def fetchWay(self, wayId: int) -> Way:
        way = self._fetchWay(wayId)
        return Way(
            type=way["type"],
            id=way["id"],
            tags=way["tags"],
            nodes=[self.fetchNode(nodeId=nodeId) for nodeId in way["nodes"]],
        )

    @cache.memoize()
    def _fetchWay(self, wayId: int):
        url = f"{OPENSTREETMAP_API}/way/{wayId}.json"
        return httpx.get(url).json()["elements"][0]

    def fetchNode(self, nodeId: int) -> Node:
        node = self._fetchNode(nodeId)
        return Node(
            type=node["type"],
            id=node["id"],
            tags=node["tags"] if "tags" in node else dict(),
            lat=node["lat"],
            lon=node["lon"],
        )

    @cache.memoize()
    def _fetchNode(self, nodeId: int):
        url = f"{OPENSTREETMAP_API}/node/{nodeId}.json"
        return httpx.get(url).json()["elements"][0]

    def fetchRelation(self, relationId: int) -> Relation:
        relation = self._fetchRelation(relationId)
        return Relation(
            type=relation["type"],
            id=relation["id"],
            members=[
                RelationMember(
                    type=member["type"],
                    ref=member["ref"],
                    role=member["role"],
                    element=self.fetchElement(
                        elementId=member["ref"], elementType=member["type"]
                    ),
                )
                for member in relation["members"]
            ],
            tags=relation["tags"],
        )

    @cache.memoize()
    def _fetchRelation(self, relationId: int):
        url = f"{OPENSTREETMAP_API}/relation/{relationId}.json"
        return httpx.get(url).json()["elements"][0]
