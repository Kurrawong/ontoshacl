"""__main__.py

CLI Entrypoint for ontoshacl
"""

from pathlib import Path

import ontoshacl
from ontoshacl.config import Configuration
from ontoshacl.core import Ontology, Shacl


def cli():
    """CLI Entrypoint"""
    # ------------------------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------------------------ #

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
    # ------------------------------------------------------------------------------------ #
    # Ontology Conversion
    # ------------------------------------------------------------------------------------ #
    print(f"OntoSHACL:v{ontoshacl.__version__}")
    print("-" * 80)
    print(
        f"\nExtracting SHACL Rules from the OWL Ontology at:\n\n\t{final_config['src']}\n\n"
    )

    # Create Ontology and Shacl instances
    ont = Ontology(src=final_config["src"], uri=final_config["uri"])

    # Prepare shacl options
    shacl_opts = {
        "base_ontology_prefix": final_config["base_ontology_prefix"],
        "namespace": final_config["namespace"],
        "versionIRI": final_config["versionIRI"],
        "creator": final_config["creator"],
        "name": final_config["name"],
        "description": final_config["description"],
        "publisher": final_config["publisher"],
        "dateCreated": final_config["dateCreated"],
        "include_domain_range_restrictions": final_config[
            "include_domain_range_restrictions"
        ],
        "domain_range_restriction_severity": final_config[
            "domain_range_restriction_severity"
        ],
        "creator_type": final_config["creator_type"],
        "creator_name": final_config["creator_name"],
        "creator_email": final_config["creator_email"],
        "creator_url": final_config["creator_url"],
        "publisher_type": final_config["publisher_type"],
        "publisher_name": final_config["publisher_name"],
        "publisher_email": final_config["publisher_email"],
        "publisher_url": final_config["publisher_url"],
    }

    shacl = Shacl(base_ontology=ont, **shacl_opts)

    # Write output
    target_path = Path(final_config["target"])
    target_path.write_text(str(shacl))

    print(
        f"Generated\n"
        f"\n"
        f"\t{len(shacl.node_shapes())} sh:NodeShape's\n"
        f"\t{len(shacl.property_shapes())} sh:PropertyShape's\n"
        f"\n"
        f"\t{target_path}"
    )
    # ------------------------------------------------------------------------------------ #
    # End
    # ------------------------------------------------------------------------------------ #


if __name__ == "__main__":
    cli()
