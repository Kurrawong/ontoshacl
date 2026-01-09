"""core.py

Core classes for Shacl generation
"""

import datetime
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from urllib.parse import urlparse

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SDO, SH, XSD

import ontoshacl


@dataclass(frozen=True)
class Restriction:
    on_klass: tuple[URIRef]
    on_property: [URIRef]
    min_cardinality: Literal | None = None
    max_cardinality: Literal | None = None
    # TODO: handle other resriction predicates


class Ontology:
    def __init__(self, src: Path, uri: URIRef):
        self.graph = Graph().parse(src)
        self.graph.bind(":", str(uri))
        self.identifier = uri

    def classes(
        self, in_domain_of: URIRef | None = None, in_range_of: URIRef | None = None
    ) -> set[URIRef]:
        """Get all owl:Class's defined in the ontology

        optionally restricted to those that are in the range or domain of
        a given owl:ObjectProperty .
        """
        assert not all(
            [in_domain_of, in_range_of]
        ), "domain and range cannot be given at the same time"

        all_klasses = {
            klass
            for klass in self.graph.subjects(RDF.type, OWL.Class)
            if not isinstance(klass, BNode)
            and str(klass).startswith(str(self.identifier))
        }
        if in_domain_of:
            return {
                klass
                for klass in self.graph.objects(in_domain_of, RDFS.range)
                if klass in all_klasses
            }
        if in_range_of:
            return {
                klass
                for klass in self.graph.objects(in_range_of, RDFS.range)
                if klass in all_klasses
            }
        return all_klasses

    def properties(
        self, with_domain: URIRef | None = None, with_range: URIRef | None = None
    ) -> list[URIRef]:
        """Get all owl:ObjectProperty's defined in the ontology
        optionally restricted to those with the given rdfs:domain or rdfs:range
        """

        assert not all(
            [with_domain, with_range]
        ), "domain and range cannot be given at the same time"

        assert any([with_domain, with_range]), "One of domain or range must be given"

        pred, obj = (
            (RDFS.domain, with_domain) if with_domain else (RDFS.range, with_range)
        )
        assert (
            obj in self.classes()
        ), f"{object} is not an owl:Class defined in this ontology"

        return {
            prop
            for prop in self.graph.subjects(pred, obj)
            if not isinstance(prop, BNode)
            and str(prop).startswith(str(self.identifier))
        }

    def restrictions(self, for_klass: URIRef) -> set[Restriction]:
        """Get all owl:Restrictions as Restriction objects

        Optionally limited to restrictions on a given owl:Class
        """

        restrictions = []
        restriction_uris = {
            uri for uri in self.graph.subjects(RDF.type, OWL.Restriction)
        }
        if for_klass:
            subklass_uris = {
                uri for uri in self.graph.objects(for_klass, RDFS.subClassOf)
            }
            restriction_uris = restriction_uris.intersection(subklass_uris)
        for restriction_uri in restriction_uris:
            on_klass = self.graph.value(restriction_uri, OWL.onClass, None)
            if isinstance(on_klass, BNode):
                union_bnode = self.graph.value(on_klass, OWL.unionOf, None)
                on_klass = tuple(Collection(self.graph, union_bnode))
            else:
                on_klass = (on_klass,)
            on_property = self.graph.value(restriction_uri, OWL.onProperty, None)
            min_cardinality = self.graph.value(
                restriction_uri, OWL.minQualifiedCardinality, None, default=None
            )
            if min_cardinality:
                min_cardinality = Literal(min_cardinality, datatype=XSD.integer)
            # TODO: handle unqualified min_cardinality
            max_cardinality = self.graph.value(
                restriction_uri, OWL.maxQualifiedCardinality, None, default=None
            )
            if max_cardinality:
                max_cardinality = Literal(max_cardinality, datatype=XSD.integer)
            # TODO: handle unqualified max_cardinality
            restriction = Restriction(
                on_klass=on_klass,
                on_property=on_property,
                min_cardinality=min_cardinality,
                max_cardinality=max_cardinality,
            )
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
    ):
        self.identifier = URIRef(namespace)
        self.shape = namespace
        self.ont = base_ontology
        self.include_domain_range_restrictions = include_domain_range_restrictions
        self.domain_range_restriction_severity = domain_range_restriction_severity
        self.graph = Graph()
        self.graph.bind("", self.identifier)
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
        description = (
            description or f"OntoShacl generated validator for {self.ont.identifier}"
        )
        self.graph.add((self.identifier, SDO.description, Literal(description)))
        name = name or f"{self.ont.identifier} Validator"
        self.graph.add((self.identifier, SDO.name, Literal(name)))
        if publisher:
            self.graph.add((self.identifier, SDO.publisher, publisher))
        # --------------------------------------------------------------------------------

        # Generate nodeshapes for each owl:Class in the base ontology
        for klass in self.ont.classes():
            self.add_nodeshape(klass)

    def add_nodeshape(
        self,
        klass: URIRef,
    ):
        """Add a sh:NodeShape for the given class

        Adds SHACL rules to the graph based on owl:Restrictions and rdfs:domain/rdfs:range
        statements found in the base ontology.

        Optionally, you can omit the domain/range rules by setting `include_domain_range_restrictions=False`
        """
        shape_uri = self.compute_shape_uri(klass)
        self.graph.add((shape_uri, RDF.type, SH.NodeShape))
        self.graph.add((shape_uri, RDFS.isDefinedBy, URIRef(self.identifier)))
        self.graph.add((shape_uri, SH.targetClass, klass))

        klass_properties = self.ont.properties(with_domain=klass)

        # Add rdfs:domain/range rules
        if self.include_domain_range_restrictions:
            for prop in klass_properties:
                prop_klasses = self.ont.classes(in_range_of=prop)
                # If there aren't any owl:class's in range of this property, then we don't have
                # any SHACL rules to add for this property path, so just continue.
                if len(prop_klasses) < 1:
                    continue

                property_shape = self.compute_shape_uri(property=prop)
                self.graph.add((shape_uri, SH.property, property_shape))
                self.graph.add((property_shape, RDF.type, SH.PropertyShape))
                self.graph.add((property_shape, SH.path, prop))
                self.graph.add(
                    (
                        property_shape,
                        SH.severity,
                        self.domain_range_restriction_severity,
                    )
                )

                if len(prop_klasses) == 1:
                    self.graph.add((property_shape, SH["class"], list(prop_klasses)[0]))
                elif len(prop_klasses) > 1:
                    collection = Collection(self.graph, BNode())
                    for prop_klass in prop_klasses:
                        k = BNode()
                        self.graph.add((k, SH["class"], prop_klass))
                        collection.append(k)
                    self.graph.add((property_shape, SH["or"], collection.uri))

        # Add owl:Restriction rules
        for restriction in self.ont.restrictions(for_klass=klass):
            prop = restriction.on_property
            property_shape = self.compute_shape_uri(prop)
            self.graph.add((shape_uri, SH.property, property_shape))
            self.graph.add((property_shape, RDF.type, SH.PropertyShape))
            self.graph.add((property_shape, SH.path, restriction.on_property))
            # Override the severity set by domain/range rules
            # owl:Restriction's should always trigger a Violation
            self.graph.remove(
                (
                    property_shape,
                    SH.severity,
                    self.domain_range_restriction_severity,
                )
            )
            self.graph.add((property_shape, SH.severity, SH.Violation))

            if len(restriction.on_klass) == 1:
                self.graph.add((property_shape, SH["class"], restriction.on_klass[0]))
            elif len(restriction.on_klass) > 1:
                collection = Collection(self.graph, BNode())
                for restriction_klass in restriction.on_klass:
                    k = BNode()
                    self.graph.add((k, SH["class"], restriction_klass))
                    collection.append(k)
                self.graph.add((property_shape, SH["or"], collection.uri))

            if restriction.min_cardinality:
                self.graph.add(
                    (property_shape, SH.minCount, restriction.min_cardinality)
                )

            if restriction.max_cardinality:
                self.graph.add(
                    (property_shape, SH.maxCount, restriction.max_cardinality)
                )

        # Add a sh:message for each property shape
        for property_shape in self.property_shapes(for_nodeshape=shape_uri):
            klass_str = klass.n3(namespace_manager=self.graph.namespace_manager)
            path_str = self.graph.value(property_shape, SH.path, None).n3(
                namespace_manager=self.graph.namespace_manager
            )
            sh_klasses = []
            sh_klass = self.graph.value(property_shape, SH["class"], None, default=None)
            if sh_klass is None:
                or_bnode = self.graph.value(property_shape, SH["or"], None)
                sh_klass_bnodes = tuple(Collection(self.graph, or_bnode))
                for sh_klass_bnode in sh_klass_bnodes:
                    sh_klass = self.graph.value(sh_klass_bnode, SH["class"], None)
                    sh_klasses.append(sh_klass)
            else:
                sh_klasses.append(sh_klass)
            min = self.graph.value(property_shape, SH.minCount, None)
            max = self.graph.value(property_shape, SH.maxCount, None)

            if not any([min, max, sh_klasses]):
                return
            message = ""

            # Min/max statements
            if all([min, max]):
                if min == max:
                    message += f"\n- A {klass_str} must be the target of exactly {min} {path_str} statements"
                else:
                    message += f"\n- A {klass_str} must have between {min} and {max} {path_str} statements"
            elif min:
                message += (
                    f"\n- A {klass_str} must have at least {min} {path_str} statements"
                )
            elif max:
                message += f"\n- A {klass_str} must not have more than {max - 1} {path_str} statements"

            # Class statements
            if len(sh_klasses) > 0:
                message += f"\n- The object of the {path_str} property on a {klass_str} must be "
                if len(sh_klasses) > 1:
                    message += "one of " + pformat(
                        [
                            sh_klass.n3(namespace_manager=self.graph.namespace_manager)
                            for sh_klass in sh_klasses
                        ]
                    )
                else:
                    message += f"a {sh_klasses[0].n3(namespace_manager=self.graph.namespace_manager)}"
            self.graph.add((property_shape, SH.message, Literal(message)))

    def node_shapes(self, for_klass: URIRef | None = None) -> set[URIRef]:
        """Get all sh:NodeShape's from the graph

        optionally restricted to just the nodeshapes targeting a specific owl:Class
        """
        nodeshapes = {ns for ns in self.graph.subjects(RDF.type, SH.NodeShape)}
        if for_klass:
            filtered = {ns for ns in self.graph.subjects(SH.targetClass, for_klass)}
            return nodeshapes.intersection(filtered)
        return nodeshapes

    def property_shapes(self, for_nodeshape: URIRef | None = None) -> set[BNode]:
        """Get the list of sh:PropertyShape's for the given node shape

        optionally filtered to just the property shapes of the given sh:NodeShape
        """
        property_shapes = {ps for ps in self.graph.subjects(RDF.type, SH.PropertyShape)}
        if for_nodeshape:
            filtered = {ps for ps in self.graph.objects(for_nodeshape, SH.property)}
            return property_shapes.intersection(filtered)
        return property_shapes

    def compute_shape_uri(
        self, klass: URIRef | None = None, property: URIRef | None = None
    ) -> URIRef:
        """Get an IRI for a new NodeShape or PropertyShape"""
        assert not all(
            [klass, property]
        ), "Only one of klass / property should be given"
        suffix = "-NS" if klass else "-PS"
        target = klass if klass else property
        parse_result = urlparse(str(target))
        fragment = parse_result.fragment
        path_part = parse_result.path.split("/")[-1]
        shape_name = f"{fragment}{suffix}" if fragment else f"{path_part}{suffix}"
        shape_uri = self.shape[shape_name]
        return shape_uri

    def __repr__(self):
        return self.graph.serialize(format="longturtle")
