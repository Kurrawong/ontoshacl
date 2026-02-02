"""core.py

Core classes for Shacl generation
"""

import datetime
import warnings
from pathlib import Path
from urllib.parse import urlparse

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, RDF, RDFS, SDO, SH, SKOS, XSD

import ontoshacl


class Klass:
    """Represents an owl:Class"""

    def __init__(self, uri: URIRef):
        self.uri = uri

    @property
    def name(self) -> str:
        """The last part of the URI"""
        parse_result = urlparse(str(self.uri))
        fragment = parse_result.fragment
        path_part = parse_result.path.split("/")[-1]
        return fragment or path_part


class ObjectProperty:
    """Represents an owl:ObjectProperty in an Ontology"""

    def __init__(self, uri: URIRef, ontology_graph: Graph):
        self.uri = uri
        self.graph = ontology_graph

    @property
    def name(self) -> str:
        """The last part of the URI"""
        parse_result = urlparse(str(self.uri))
        fragment = parse_result.fragment
        path_part = parse_result.path.split("/")[-1]
        return fragment or path_part

    @property
    def domain(self) -> set[Klass]:
        """owl:Classes in the rdfs:domain of the property"""
        klasses = {
            Klass(uri=uri) for uri in self.graph.objects(self.uri, RDFS.domain, None)
        }
        return klasses

    @property
    def range(self) -> set[Klass]:
        """owl:Classes in the rdfs:range of the property"""
        klasses = {
            Klass(uri=uri) for uri in self.graph.objects(self.uri, RDFS.range, None)
        }
        return klasses


class Restriction:
    """Represents an owl:Restriction in an Ontology"""

    def __init__(self, uri: URIRef, ontology_graph: Graph):
        self.uri = uri
        self.graph = ontology_graph

    @property
    def subklass(self) -> URIRef:
        klass_uri = self.graph.value(None, RDFS.subClassOf, self.uri)
        return Klass(uri=klass_uri)

    @property
    def on_klass(self) -> set[Klass]:
        klass_uri_or_bnode = self.graph.value(self.uri, OWL.onClass, None)
        if isinstance(klass_uri_or_bnode, BNode):
            union_bnode = self.graph.value(klass_uri_or_bnode, OWL.unionOf, None)
            return {Klass(uri=uri) for uri in Collection(self.graph, union_bnode)}
        return set((Klass(uri=klass_uri_or_bnode),))

    @property
    def on_property(self) -> URIRef:
        property_uri = self.graph.value(self.uri, OWL.onProperty, None)
        return ObjectProperty(uri=property_uri, ontology_graph=self.graph)

    @property
    def min_cardinality(self) -> Literal | None:
        mc = self.graph.value(self.uri, OWL.minQualifiedCardinality, None)
        if not mc:
            return None
        return Literal(mc, datatype=XSD.integer)

    @property
    def max_cardinality(self) -> Literal | None:
        mc = self.graph.value(self.uri, OWL.maxQualifiedCardinality, None)
        if not mc:
            return None
        return Literal(mc, datatype=XSD.integer)

    @property
    def has_self(self) -> bool:
        hs = self.graph.value(self.uri, OWL.hasSelf, None)
        if not hs:
            return False
        return True


class Ontology:
    def __init__(self, src: Path, uri: URIRef):
        self.graph = Graph().parse(src)
        self.graph.bind(":", str(uri))
        self.identifier = uri

    def classes(self) -> set[Klass]:
        """Get all owl:Class's defined in the ontology"""
        klasses = set()
        klass_uris = {
            uri
            for uri in self.graph.subjects(RDF.type, OWL.Class)
            if uri.startswith(str(self.identifier))
        }
        for klass_uri in klass_uris:
            klass = Klass(uri=klass_uri)
            klasses.add(klass)
        return klasses

    def properties(self) -> set[ObjectProperty]:
        """Get all owl:ObjectProperty's defined in the ontology"""

        object_properties = set()
        object_property_uris = {
            uri
            for uri in self.graph.subjects(RDF.type, OWL.ObjectProperty)
            if uri.startswith(str(self.identifier))
        }
        for object_property_uri in object_property_uris:
            object_property = ObjectProperty(
                uri=object_property_uri, ontology_graph=self.graph
            )
            object_properties.add(object_property)

        return object_properties

    def restrictions(self) -> set[Restriction]:
        """Get all owl:Restrictions as Restriction objects"""

        restrictions = []
        restriction_uris = {
            uri for uri in self.graph.subjects(RDF.type, OWL.Restriction)
        }
        for restriction_uri in restriction_uris:
            restriction = Restriction(uri=restriction_uri, ontology_graph=self.graph)
            restrictions.append(restriction)
        return restrictions


class Shacl:
    def __init__(
        self,
        base_ontology: Ontology,
        namespace: Namespace,
        versionIRI: URIRef,
        creator: URIRef,
        dateCreated: Literal | None = None,
        name: Literal | None = None,
        description: Literal | None = None,
        publisher: URIRef | None = None,
        base_ontology_prefix: str | None = None,
        include_domain_range_restrictions: bool = True,
        domain_range_restriction_severity: URIRef = SH.Warning,
        creator_type: str = "person",
        creator_name: Literal | None = None,
        creator_email: Literal | None = None,
        creator_url: Literal | None = None,
        publisher_type: str = "person",
        publisher_name: Literal | None = None,
        publisher_email: Literal | None = None,
        publisher_url: Literal | None = None,
    ):
        self.identifier = URIRef(namespace.strip("/#"))
        self.shape = namespace
        self.ont = base_ontology
        self.include_domain_range_restrictions = include_domain_range_restrictions
        self.domain_range_restriction_severity = domain_range_restriction_severity
        self.graph = Graph()
        self.graph.bind("ont", self.identifier)
        self.graph.bind("", self.shape)
        if base_ontology_prefix:
            self.graph.bind(base_ontology_prefix, self.ont.identifier)

        # Add Ontology metadata for the new validator ontology
        # --------------------------------------------------------------------------------
        self.graph.add((self.identifier, RDF.type, OWL.Ontology))
        self.graph.add((self.identifier, OWL.versionIRI, versionIRI))
        self.graph.add(
            (
                self.identifier,
                OWL.versionInfo,
                Literal(
                    f"{versionIRI.n3(namespace_manager=self.graph.namespace_manager)} Generated by OntoShacl:v{ontoshacl.__version__} <https://github.com/Kurrawong/ontoshacl>"
                ),
            )
        )
        self.graph.add((self.identifier, SDO.creator, creator))
        dateModified = datetime.date.today().isoformat()
        dateCreated = dateCreated or dateModified
        self.graph.add(
            (self.identifier, SDO.dateCreated, Literal(dateCreated, datatype=XSD.date))
        )
        self.graph.add(
            (
                self.identifier,
                SDO.dateModified,
                Literal(dateModified, datatype=XSD.date),
            )
        )
        self.graph.add(
            (self.identifier, SDO.dateIssued, Literal(dateModified, datatype=XSD.date))
        )
        description = (
            description or f"OntoShacl generated validator for {self.ont.identifier}"
        )
        self.graph.add((self.identifier, SDO.description, Literal(description)))
        name = name or f"{self.ont.identifier} Validator"
        self.graph.add((self.identifier, SDO.name, Literal(name)))
        if publisher:
            self.graph.add((self.identifier, SDO.publisher, publisher))
        self.graph.add(
            (
                self.identifier,
                SKOS.historyNote,
                Literal(f"Automatically generated by OntoShacl on {dateModified}"),
            )
        )
        self.graph.add((self.identifier, PROV.wasDerivedFrom, self.ont.identifier))
        self.graph.add(
            (
                self.identifier,
                SDO.codeRepository,
                Literal("https://github.com/kurrawong/ontoshacl", datatype=XSD.anyURI),
            )
        )
        self.graph.add(
            (
                self.identifier,
                SDO.license,
                Literal(
                    "https://creativecommons.org/licenses/by/4.0/", datatype=XSD.anyURI
                ),
            )
        )
        self.graph.add((self.identifier, SDO.copyrightHolder, publisher))
        self.graph.add(
            (
                self.identifier,
                SDO.copyrightYear,
                Literal(datetime.date.today().year, datatype=XSD.integer),
            )
        )
        # Add creator metadata
        if creator_type == "person":
            self.graph.add((creator, RDF.type, SDO.Person))
            if creator_name:
                self.graph.add((creator, SDO.name, creator_name))
            if creator_email:
                self.graph.add((creator, SDO.email, creator_email))
        else:  # organisation
            self.graph.add((creator, RDF.type, SDO.Organization))
            if creator_name:
                self.graph.add((creator, SDO.name, creator_name))
            if creator_url:
                self.graph.add((creator, SDO.url, creator_url))

        # Add publisher metadata
        if publisher and publisher_type == "person":
            self.graph.add((publisher, RDF.type, SDO.Person))
            if publisher_name:
                self.graph.add((publisher, SDO.name, publisher_name))
            if publisher_email:
                self.graph.add((publisher, SDO.email, publisher_email))
        elif publisher and publisher_type == "organisation":
            self.graph.add((publisher, RDF.type, SDO.Organization))
            if publisher_name:
                self.graph.add((publisher, SDO.name, publisher_name))
            if publisher_url:
                self.graph.add((publisher, SDO.url, publisher_url))
        # --------------------------------------------------------------------------------

        # Add sh:PropertyShape's from the owl:ObjectProperty's in the base ontology
        for prop in self.ont.properties():
            self.add_property_shape(from_property=prop)

        # Add sh:PropertyShape's from the owl:Restriction's in the base ontology
        for restriction in self.ont.restrictions():
            if not restriction.on_klass or restriction.on_property:
                warnings.warn(
                    "Found a restriction with no rules that we know how to process yet"
                )
                continue
            self.add_property_shape(from_restriction=restriction)

        # Add sh:NodeShape's for each owl:Class in the base ontology
        for klass in self.ont.classes():
            self.add_node_shape(klass)

    def add_node_shape(
        self,
        klass: Klass,
    ):
        """Add a sh:NodeShape for the given class"""
        node_shape_uri = self.compute_shape_uri(klass)
        property_shapes = self.property_shapes(for_nodeshape=node_shape_uri)
        if property_shapes:
            self.graph.add((node_shape_uri, RDF.type, SH.NodeShape))
            self.graph.add(
                (node_shape_uri, SKOS.prefLabel, Literal(f"{klass.name} Shape"))
            )
            self.graph.add((node_shape_uri, RDFS.isDefinedBy, self.identifier))
            self.graph.add((node_shape_uri, PROV.wasDerivedFrom, klass.uri))
            self.graph.add((node_shape_uri, SH.targetClass, klass.uri))
            self.graph.add(
                (node_shape_uri, SH.message, Literal(f"{klass.name} validation"))
            )
        return

    def add_property_shape(
        self,
        from_property: ObjectProperty | None = None,
        from_restriction: Restriction | None = None,
    ):
        """Add a sh:PropertyShape for the given property or restriction"""

        if from_property:
            if not self.include_domain_range_restrictions:
                return
            target_klasses = from_property.domain
            target_property = from_property
            property_shape_uri = self.compute_shape_uri(from_property)
            severity = self.domain_range_restriction_severity
            sh_klasses = from_property.range
            min_cardinality = None
            max_cardinality = None

        if from_restriction:
            target_klasses = set([from_restriction.subklass])
            target_property = from_restriction.on_property
            property_shape_uri = self.compute_shape_uri(from_restriction)
            severity = SH.Violation
            sh_klasses = from_restriction.on_klass
            min_cardinality = from_restriction.min_cardinality
            max_cardinality = from_restriction.max_cardinality

        for target_klass in target_klasses:
            node_shape_uri = self.compute_shape_uri(target_klass)
            self.graph.add((node_shape_uri, SH.property, property_shape_uri))
        self.graph.add((property_shape_uri, RDF.type, SH.PropertyShape))
        self.graph.add(
            (
                property_shape_uri,
                SKOS.prefLabel,
                Literal(f"{target_property.name} Shape"),
            )
        )
        self.graph.add((property_shape_uri, PROV.wasDerivedFrom, target_property.uri))
        self.graph.add((property_shape_uri, SH.path, target_property.uri))
        self.graph.add((property_shape_uri, SH.severity, severity))
        if min_cardinality:
            self.graph.add((property_shape_uri, SH.minCount, min_cardinality))
        if max_cardinality:
            self.graph.add((property_shape_uri, SH.maxCount, max_cardinality))
        if len(sh_klasses) == 1:
            sh_klass = next(iter(sh_klasses))
            self.graph.add((property_shape_uri, SH["class"], sh_klass.uri))
        elif len(sh_klasses) > 1:
            collection = Collection(self.graph, BNode())
            for sh_klass in sh_klasses:
                k = BNode()
                self.graph.add((k, SH["class"], sh_klass.uri))
                collection.append(k)
            self.graph.add((property_shape_uri, SH["or"], collection.uri))
        message = self.get_message(
            for_property_shape=property_shape_uri, target_klasses=target_klasses
        )
        if message:
            self.graph.add((property_shape_uri, SH.message, message))
        return

    def get_message(
        self, for_property_shape: URIRef, target_klasses: list[Klass] = []
    ) -> Literal | None:
        """Generate an informative error message for the given property shape"""

        path_str = self.graph.value(for_property_shape, SH.path, None).n3(
            namespace_manager=self.graph.namespace_manager
        )
        sh_klasses = []
        sh_klass = self.graph.value(for_property_shape, SH["class"], None, default=None)
        if sh_klass is None:
            or_bnode = self.graph.value(for_property_shape, SH["or"], None)
            sh_klass_bnodes = tuple(Collection(self.graph, or_bnode))
            for sh_klass_bnode in sh_klass_bnodes:
                sh_klass = self.graph.value(sh_klass_bnode, SH["class"], None)
                sh_klasses.append(sh_klass)
        else:
            sh_klasses.append(sh_klass)
        min = self.graph.value(for_property_shape, SH.minCount, None)
        max = self.graph.value(for_property_shape, SH.maxCount, None)

        message = ""
        if target_klasses:
            message += f"\nThe subject of a {path_str} statement must be one of:\n\t- "
            message += "\n\t- ".join(
                [
                    klass.uri.n3(namespace_manager=self.graph.namespace_manager)
                    for klass in target_klasses
                ]
            )
            message += "\n"
        # sh:class statements
        if sh_klasses:
            message += f"\nThe object of a {path_str} statement must be one of:\n\t- "
            message += "\n\t- ".join(
                [
                    sh_klass.n3(namespace_manager=self.graph.namespace_manager)
                    for sh_klass in sh_klasses
                ]
            )
            message += "\n"
        # Min/max statements
        if any([min, max]):
            message += f"\nThe {path_str} property MUST:"
            if min == max:
                message += f"\n\t- Appear exactly {min} times"
            elif min and max:
                message += f"\n\t- Appear between {min} and {max} times"
            elif min:
                message += f"\n\t- Appear at least {min} times"
            elif max:
                message += f"\n\t- Appear no more than {max - 1} times"

        return Literal(message)

    def node_shapes(self, for_klass: URIRef | None = None) -> set[URIRef]:
        """Get all sh:NodeShape's from the graph

        optionally restricted to just the nodeshapes targeting a specific owl:Class
        """
        nodeshapes = {ns for ns in self.graph.subjects(RDF.type, SH.NodeShape)}
        if for_klass:
            filtered = {ns for ns in self.graph.subjects(SH.targetClass, for_klass)}
            return nodeshapes.intersection(filtered)
        return nodeshapes

    def property_shapes(self, for_nodeshape: URIRef | None = None) -> set[URIRef]:
        """Get the list of sh:PropertyShape's for the given node shape

        optionally filtered to just the property shapes of the given sh:NodeShape
        """
        property_shapes = {ps for ps in self.graph.subjects(RDF.type, SH.PropertyShape)}
        if for_nodeshape:
            filtered = {ps for ps in self.graph.objects(for_nodeshape, SH.property)}
            return property_shapes.intersection(filtered)
        return property_shapes

    def compute_shape_uri(
        self, for_object: Klass | ObjectProperty | Restriction
    ) -> URIRef:
        """Generate a URI for a new NodeShape or PropertyShape"""
        prefix = ""
        suffix = "-Shape"
        if isinstance(for_object, Restriction):
            prefix = for_object.subklass.name
            name = for_object.on_property.name
        else:
            name = for_object.name
        shape_name = f"{prefix}{name}{suffix}"
        shape_uri = self.shape[shape_name]
        return shape_uri

    def __repr__(self):
        return self.graph.serialize(format="longturtle")
