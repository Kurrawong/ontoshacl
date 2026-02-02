"""config.py

Configuration parsing and handling
"""

import argparse
import json
from pathlib import Path

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import SH, XSD


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
            "creator_type": "person",  # person or organisation
            "creator_name": None,
            "creator_email": None,
            "creator_url": None,
            "name": None,
            "description": None,
            "publisher": None,
            "publisher_type": "person",  # person or organisation
            "publisher_name": None,
            "publisher_email": None,
            "publisher_url": None,
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
        parser.add_argument("--src", help="Path to source ontology file", default=None)
        parser.add_argument("--uri", help="URI for the base ontology", default=None)

        # Target Validator details
        parser.add_argument(
            "--target", help="Path to output SHACL rules file", default=None
        )
        parser.add_argument(
            "--namespace", help="Namespace for the validator ontology", default=None
        )
        parser.add_argument(
            "--versionIRI", help="Version IRI for the validator ontology", default=None
        )
        parser.add_argument(
            "--creator", help="Creator URI for the validator ontology", default=None
        )
        parser.add_argument(
            "--creator-type",
            help="Creator type (person or organisation)",
            choices=["person", "organisation"],
            default=None,
        )
        parser.add_argument("--creator-name", help="Creator name", default=None)
        parser.add_argument(
            "--creator-email", help="Creator email (for person)", default=None
        )
        parser.add_argument(
            "--creator-url", help="Creator URL (for organisation)", default=None
        )
        parser.add_argument(
            "--name", help="Name for the validator ontology", default=None
        )
        parser.add_argument(
            "--description", help="Description for the validator ontology", default=None
        )
        parser.add_argument(
            "--publisher", help="Publisher URI for the validator ontology", default=None
        )
        parser.add_argument(
            "--publisher-type",
            help="Publisher type (person or organisation)",
            choices=["person", "organisation"],
            default=None,
        )
        parser.add_argument("--publisher-name", help="Publisher name", default=None)
        parser.add_argument(
            "--publisher-email", help="Publisher email (for person)", default=None
        )
        parser.add_argument(
            "--publisher-url", help="Publisher URL (for organisation)", default=None
        )
        parser.add_argument(
            "--dateCreated",
            help="Creation date for the validator ontology (YYYY-MM-DD)",
            default=None,
        )
        parser.add_argument(
            "--base-ontology-prefix", help="Prefix for the base ontology", default=None
        )

        # SHACL Generation options
        parser.add_argument(
            "--include-domain-range-restrictions",
            help="Include domain/range restrictions",
            action="store_true",
            default=None,
        )
        parser.add_argument(
            "--no-domain-range-restrictions",
            help="Exclude domain/range restrictions",
            action="store_false",
            dest="include_domain_range_restrictions",
        )
        parser.add_argument(
            "--domain-range-restriction-severity",
            help="Severity level for domain/range restrictions (SH.Warning, SH.Violation, SH.Info)",
            default=None,
        )

        # Configuration file
        parser.add_argument(
            "--config", help="Path to JSON configuration file", default=None
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
            with open(config_file, "r") as f:
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
        literal_fields = [
            "name",
            "description",
            "creator_name",
            "creator_email",
            "creator_url",
            "publisher_name",
            "publisher_email",
            "publisher_url",
        ]
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
            "SH.Info": SH.Info,
        }
        if isinstance(config["domain_range_restriction_severity"], str):
            config["domain_range_restriction_severity"] = severity_map.get(
                config["domain_range_restriction_severity"], SH.Warning
            )

        # Convert boolean strings to boolean values
        if isinstance(config["include_domain_range_restrictions"], str):
            config["include_domain_range_restrictions"] = config[
                "include_domain_range_restrictions"
            ].lower() in ["true", "1", "yes"]

        # Convert contact info URLs to proper datatype
        if config["creator_email"] and isinstance(config["creator_email"], Literal):
            config["creator_email"] = Literal(
                str(config["creator_email"]), datatype=XSD.anyURI
            )
        if config["publisher_email"] and isinstance(config["publisher_email"], Literal):
            config["publisher_email"] = Literal(
                str(config["publisher_email"]), datatype=XSD.anyURI
            )
        if config["creator_url"] and isinstance(config["creator_url"], Literal):
            config["creator_url"] = Literal(
                str(config["creator_url"]), datatype=XSD.anyURI
            )
        if config["publisher_url"] and isinstance(config["publisher_url"], Literal):
            config["publisher_url"] = Literal(
                str(config["publisher_url"]), datatype=XSD.anyURI
            )

        return config

    def validate(self):
        """Validate the configuration"""
        required_fields = ["src", "uri", "target", "namespace", "creator"]

        missing_fields = []
        for field in required_fields:
            if not self.config[field]:
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )

        # Validate paths
        if self.config["src"]:
            src_path = Path(self.config["src"])
            if not src_path.exists():
                raise ValueError(f"Source ontology file does not exist: {src_path}")

        return True
