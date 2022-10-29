import overpy

from configuration import (
    OVERPASS_URL,
    cache,
)
from source.osmSource import Way, Relation, RelationMember, Node, OSMSource


class OSMOverpass(OSMSource):
    def __init__(self) -> None:
        super().__init__()
        self.overpassApi = overpy.Overpass(url=OVERPASS_URL)
        self.overpassRelations = dict()
        self.overpassWays = dict()
        self.overpassNodes = dict()

    @cache.memoize()
    def _getRelationDataFromOverpass(self, relationId: int):
        query = f"""
        [out:json][timeout:250];
        relation(id:{relationId});
        (._;>>;);
        out body;
        """
        return self.overpassApi.query(query)

    def _saveRelationDataFromOverpass(self, relationId: int):
        overpassResult = self._getRelationDataFromOverpass(relationId)
        for relation in overpassResult.relations:
            self.overpassRelations[relation.id] = relation
        for way in overpassResult.ways:
            self.overpassWays[way.id] = way
        for node in overpassResult.nodes:
            self.overpassNodes[node.id] = node

    def fetchNode(self, nodeId: int) -> Node:
        node = self.overpassNodes[nodeId]

        return Node(
            type="node",
            id=node.id,
            lat=node.lat,
            lon=node.lon,
            tags=node.tags,
        )

    def fetchWay(self, wayId: int) -> Way:
        way = self.overpassWays[wayId]

        return Way(
            id=way.id,
            type="way",
            tags=way.tags,
            nodes=[self.fetchNode(node.id) for node in way.nodes],
        )

    def fetchRelation(self, relationId: int) -> Relation:
        relation = self.overpassRelations[relationId]

        def overpyType(relationMember) -> str:
            t = type(relationMember)
            if t == overpy.RelationRelation:
                return "relation"
            if t == overpy.RelationWay:
                return "way"
            if t == overpy.RelationNode:
                return "node"
            raise NotImplementedError(f"Unsupported type: {t}")

        return Relation(
            id=relation.id,
            type="relation",
            tags=relation.tags,
            members=[
                RelationMember(
                    ref=member.ref,
                    type=overpyType(member),
                    role=member.role,
                    element=self.fetchElement(
                        elementType=overpyType(member), elementId=member.ref
                    ),
                )
                for member in relation.members
            ],
        )

    def savePublicTransportRelation(self, relationId: int):
        self._saveRelationDataFromOverpass(relationId=relationId)
        super().savePublicTransportRelation(relationId)
