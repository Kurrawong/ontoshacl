"""OntoSHACL

A self contained script to generate SHACL rules from an OWL ontology.

Pseudo code implementation:

    For each class in the ontology:
      For each restriction on the class:
        - add min/max/class restriction rules
      For each property whose domain includes class:
        - add class restriction rules

> where each class is an owl:Class and each property is an owl:ObjectProperty.

The domain/range restrictions from properties can be omitted by configuration.
The default behaviour is to include them with sh:severity == sh:Warning.
The severity level can also be configured.

Helpful warning messages are automatically generated for each sh:PropertyShape

Validator ontology metadata is also included by default, this includes details
about creator, version etc.



Requirements
------

- python (tested with 3.12.12)
- rdflib (tested with 7.5.0)

Usage
------

See the if __name__ == "__main__" section at the bottom of this file
for configuration.

Basically, you just need to provide

  - the path to the source ontology, a
  - path to output the SHACL rules, and
  - the metadata details for the validator.

To run it:

```
$ python ontoshacl.py
```

"""

import argparse
import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from pprint import pformat
from urllib.parse import urlparse

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SDO, SH, XSD


class Configuration:
    """Configuration class for OntoSHACL
    
    Handles both CLI arguments and JSON configuration files.
    """
    
    def __init__(self):
        self.config = {
            # Base Ontology details
            "src": None,
            "uri": None,
            
            # Target Validator details
            "target": None,
            "namespace": None,
            "versionIRI": None,
            "creator": None,
            "name": None,
            "description": None,
            "publisher": None,
            "dateCreated": None,
            "base_ontology_prefix": None,
            
            # SHACL Generation options
            "include_domain_range_restrictions": True,
            "domain_range_restriction_severity": "SH.Warning",
        }
    
    def parse_cli_args(self):
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="OntoSHACL - Generate SHACL rules from OWL ontologies"
        )
        
        # Base Ontology details
        parser.add_argument(
            "--src", 
            help="Path to source ontology file",
            default=None
        )
        parser.add_argument(
            "--uri", 
            help="URI for the base ontology",
            default=None
        )
        
        # Target Validator details
        parser.add_argument(
            "--target", 
            help="Path to output SHACL rules file",
            default=None
        )
        parser.add_argument(
            "--namespace", 
            help="Namespace for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--versionIRI", 
            help="Version IRI for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--creator", 
            help="Creator URI for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--name", 
            help="Name for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--description", 
            help="Description for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--publisher", 
            help="Publisher URI for the validator ontology",
            default=None
        )
        parser.add_argument(
            "--dateCreated", 
            help="Creation date for the validator ontology (YYYY-MM-DD)",
            default=None
        )
        parser.add_argument(
            "--base-ontology-prefix", 
            help="Prefix for the base ontology",
            default=None
        )
        
        # SHACL Generation options
        parser.add_argument(
            "--include-domain-range-restrictions", 
            help="Include domain/range restrictions",
            action="store_true",
            default=None
        )
        parser.add_argument(
            "--no-domain-range-restrictions", 
            help="Exclude domain/range restrictions",
            action="store_false",
            dest="include_domain_range_restrictions"
        )
        parser.add_argument(
            "--domain-range-restriction-severity", 
            help="Severity level for domain/range restrictions (SH.Warning, SH.Violation, SH.Info)",
            default=None
        )
        
        # Configuration file
        parser.add_argument(
            "--config", 
            help="Path to JSON configuration file",
            default=None
        )
        
        args = parser.parse_args()
        
        # Update config from CLI args
        for key, value in vars(args).items():
            if value is not None and key in self.config:
                self.config[key] = value
        
        return args
    
    def load_from_json(self, config_file: Path):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                json_config = json.load(f)
            
            # Update config from JSON
            for key, value in json_config.items():
                if key in self.config:
                    self.config[key] = value
            
            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config file: {e}")
            return False
    
    def get_config(self):
        """Get the final configuration with proper type conversion"""
        config = self.config.copy()
        
        # Convert string URIs to URIRef objects
        uri_fields = ["uri", "namespace", "versionIRI", "creator", "publisher"]
        for field in uri_fields:
            if config[field] and isinstance(config[field], str):
                config[field] = URIRef(config[field])
        
        # Convert namespace to Namespace object if it's a URIRef
        if isinstance(config["namespace"], URIRef):
            config["namespace"] = Namespace(str(config["namespace"]))
        
        # Convert versionIRI to URIRef within namespace if it's a string
        if isinstance(config["versionIRI"], str) and config["namespace"]:
            config["versionIRI"] = config["namespace"][config["versionIRI"]]
        
        # Convert string literals to Literal objects
        literal_fields = ["name", "description"]
        for field in literal_fields:
            if config[field] and isinstance(config[field], str):
                config[field] = Literal(config[field])
        
        # Convert dateCreated to Literal with XSD.date datatype
        if config["dateCreated"] and isinstance(config["dateCreated"], str):
            config["dateCreated"] = Literal(config["dateCreated"], datatype=XSD.date)
        
        # Convert severity string to URIRef
        severity_map = {
            "SH.Warning": SH.Warning,
            "SH.Violation": SH.Violation,
            "SH.Info": SH.Info
        }
        if isinstance(config["domain_range_restriction_severity"], str):
            config["domain_range_restriction_severity"] = severity_map.get(
                config["domain_range_restriction_severity"], SH.Warning
            )
        
        # Convert boolean strings to boolean values
        if isinstance(config["include_domain_range_restrictions"], str):
            config["include_domain_range_restrictions"] = config["include_domain_range_restrictions"].lower() in ["true", "1", "yes"]
        
        return config
    
    def validate(self):
        """Validate the configuration"""
        required_fields = ["src", "uri", "target", "namespace", "creator"]
        
        missing_fields = []
        for field in required_fields:
            if not self.config[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
        
        # Validate paths
        if self.config["src"]:
            src_path = Path(self.config["src"])
            if not src_path.exists():
                raise ValueError(f"Source ontology file does not exist: {src_path}")
        
        return True


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
                    f"{versionIRI.n3(namespace_manager=self.graph.namespace_manager)} Generated by OntoShacl:v{SCRIPT_VERSION} <https://github.com/Kurrawong/ontoshacl>"
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

        prop_bnodes = dict()
        klass_properties = self.ont.properties(with_domain=klass)

        # Add rdfs:domain/range rules
        if self.include_domain_range_restrictions:
            for prop in klass_properties:
                prop_klasses = self.ont.classes(in_range_of=prop)
                # If there aren't any owl:class's in range of this property, then we don't have
                # any SHACL rules to add for this property path, so just continue.
                if len(prop_klasses) < 1:
                    continue

                prop_bnode = BNode()
                self.graph.add((shape_uri, SH.property, prop_bnode))
                self.graph.add((prop_bnode, RDF.type, SH.PropertyShape))
                self.graph.add((prop_bnode, SH.path, prop))
                self.graph.add(
                    (prop_bnode, SH.severity, self.domain_range_restriction_severity)
                )

                # Save the generated bnode so that we can add rules for the owl:Restriction's
                # on this property (if any) to the same property path.
                prop_bnodes[prop] = prop_bnode

                if len(prop_klasses) == 1:
                    self.graph.add((prop_bnode, SH["class"], list(prop_klasses)[0]))
                elif len(prop_klasses) > 1:
                    collection = Collection(self.graph, BNode())
                    for prop_klass in prop_klasses:
                        k = BNode()
                        self.graph.add((k, SH["class"], prop_klass))
                        collection.append(k)
                    self.graph.add((prop_bnode, SH["or"], collection.uri))

        # Add owl:Restriction rules
        for restriction in self.ont.restrictions(for_klass=klass):
            prop = restriction.on_property
            # If a bnode already exists for this property path then we add the restriction
            # rules to it. Otherwise we need to make a new one.
            prop_bnode = prop_bnodes.get(restriction.on_property, None)
            if prop_bnode is None:
                prop_bnode = BNode()
                self.graph.add((shape_uri, SH.property, prop_bnode))
                self.graph.add((prop_bnode, RDF.type, SH.PropertyShape))
                self.graph.add((prop_bnode, SH.path, restriction.on_property))
            else:
                # Override the severity set by domain/range rules
                # owl:Restriction's should always trigger a Violation
                self.graph.remove(
                    (prop_bnode, SH.severity, self.domain_range_restriction_severity)
                )

            self.graph.add((prop_bnode, SH.severity, SH.Violation))
            if len(restriction.on_klass) == 1:
                self.graph.add((prop_bnode, SH["class"], restriction.on_klass[0]))
            elif len(restriction.on_klass) > 1:
                collection = Collection(self.graph, BNode())
                for restriction_klass in restriction.on_klass:
                    k = BNode()
                    self.graph.add((k, SH["class"], restriction_klass))
                    collection.append(k)
                self.graph.add((prop_bnode, SH["or"], collection.uri))

            if restriction.min_cardinality:
                self.graph.add((prop_bnode, SH.minCount, restriction.min_cardinality))

            if restriction.max_cardinality:
                self.graph.add((prop_bnode, SH.maxCount, restriction.max_cardinality))

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

    def compute_shape_uri(self, klass: URIRef) -> URIRef:
        parse_result = urlparse(str(klass))
        fragment = parse_result.fragment
        path_part = parse_result.path.split("/")[-1]
        shape_name = f"{fragment}Shape" if fragment else f"{path_part}Shape"
        shape_uri = self.shape[shape_name]
        return shape_uri

    def __repr__(self):
        return self.graph.serialize(format="longturtle")


if __name__ == "__main__":
    # ------------------------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------------------------ #

    SCRIPT_VERSION = "0.0.1"

    # Initialize configuration
    config = Configuration()
    
    # Parse CLI arguments
    args = config.parse_cli_args()
    
    # Load from JSON config file if provided
    if args.config:
        config_file = Path(args.config)
        if not config.load_from_json(config_file):
            print(f"Warning: Could not load configuration from {config_file}")
    
    # Get final configuration with type conversion
    final_config = config.get_config()
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nUsage: python ontoshacl.py --help for available options")
        exit(1)

    # ------------------------------------------------------------------------------------ #
    # End
    # ------------------------------------------------------------------------------------ #

    print(f"OntoSHACL:v{SCRIPT_VERSION}")
    print("-" * 80)
    print(f"\nExtracting SHACL Rules from the OWL Ontology at:\n\n\t{final_config['src']}\n\n")

    # Create Ontology and Shacl instances
    ont = Ontology(src=final_config['src'], uri=final_config['uri'])
    
    # Prepare shacl options
    shacl_opts = {
        "base_ontology_prefix": final_config['base_ontology_prefix'],
        "namespace": final_config['namespace'],
        "versionIRI": final_config['versionIRI'],
        "creator": final_config['creator'],
        "name": final_config['name'],
        "description": final_config['description'],
        "publisher": final_config['publisher'],
        "dateCreated": final_config['dateCreated'],
        "include_domain_range_restrictions": final_config['include_domain_range_restrictions'],
        "domain_range_restriction_severity": final_config['domain_range_restriction_severity'],
    }

    shacl = Shacl(base_ontology=ont, **shacl_opts)
    
    # Write output
    target_path = Path(final_config['target'])
    target_path.write_text(str(shacl))
    
    print(
        f"Generated\n"
        f"\n"
        f"\t{len(shacl.node_shapes())} sh:NodeShape's\n"
        f"\t{len(shacl.property_shapes())} sh:PropertyShape's\n"
        f"\n"
        f"\t{target_path}"
    )
