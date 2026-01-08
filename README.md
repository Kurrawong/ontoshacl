# OntoSHACL

A self contained script to generate SHACL rules from an OWL ontology.

> [!WARNING]
> This script has been built out just enough to let me do some basic
> validation on the RiC-O ontology.
> It could be extended to do more, but it's not worth doing that right now.
> See the disclaimer below for details

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

## Usage

OntoSHACL now supports both CLI arguments and JSON configuration files for flexible configuration.

### CLI Usage

```bash
# Basic usage with required parameters
$ python ontoshacl.py \
    --src example_data/rico.ttl \
    --uri "https://www.ica.org/standards/RiC/ontology#" \
    --target output.ttl \
    --namespace "https://example.com/validator#" \
    --creator "https://example.com/people#person"

# Advanced usage with all options
$ python ontoshacl.py \
    --src example_data/rico.ttl \
    --uri "https://www.ica.org/standards/RiC/ontology#" \
    --target output.ttl \
    --namespace "https://example.com/validator#" \
    --versionIRI "1.0.0" \
    --creator "https://example.com/people#person" \
    --name "My Validator" \
    --description "SHACL validator for my ontology" \
    --publisher "https://example.com" \
    --dateCreated "2023-01-01" \
    --base-ontology-prefix "myont" \
    --domain-range-restriction-severity SH.Violation

# To see all available options
$ python ontoshacl.py --help
```

### JSON Configuration

Create a JSON configuration file (e.g., `config.json`):

```json
{
    "src": "example_data/rico.ttl",
    "uri": "https://www.ica.org/standards/RiC/ontology#",
    "target": "output.ttl",
    "namespace": "https://example.com/validator#",
    "versionIRI": "1.0.0",
    "creator": "https://example.com/people#person",
    "name": "My Validator",
    "description": "SHACL validator for my ontology",
    "publisher": "https://example.com",
    "dateCreated": "2023-01-01",
    "base_ontology_prefix": "myont",
    "include_domain_range_restrictions": true,
    "domain_range_restriction_severity": "SH.Warning"
}
```

Then run with:

```bash
$ python ontoshacl.py --config config.json
```

### Configuration Options

**Required Parameters:**
- `--src`: Path to source ontology file
- `--uri`: URI for the base ontology
- `--target`: Path to output SHACL rules file
- `--namespace`: Namespace for the validator ontology
- `--creator`: Creator URI for the validator ontology

**Optional Parameters:**
- `--versionIRI`: Version IRI for the validator ontology (default: namespace + "1.0.0")
- `--name`: Name for the validator ontology
- `--description`: Description for the validator ontology
- `--publisher`: Publisher URI for the validator ontology
- `--dateCreated`: Creation date (YYYY-MM-DD)
- `--base-ontology-prefix`: Prefix for the base ontology
- `--include-domain-range-restrictions`: Include domain/range restrictions (default: true)
- `--no-domain-range-restrictions`: Exclude domain/range restrictions
- `--domain-range-restriction-severity`: Severity level (SH.Warning, SH.Violation, SH.Info)
- `--config`: Path to JSON configuration file

**Severity Levels:**
- `SH.Warning`: Domain/range violations will be warnings
- `SH.Violation`: Domain/range violations will be violations
- `SH.Info`: Domain/range violations will be informational

## Disclaimer

This script has been tested against the RiC-O ontology only.
I'm certain there are gaps in the implementation.

Contributions welcome.

### Implmentation status

Actually implemented things

| owl                         | shacl       |
| --------------------------- | ----------- |
| rdfs:range                  | sh:class    |
| owl:onClass                 | sh:class    |
| owl:minQualifiedCardinality | sh:minCount |
| owl:maxQualifiedCardinality | sh:maxCount |

See table from <https://spinrdf.org/shacl-and-owl.html> for an idea of what
else could be implemented.

## Contact

Lawson Lewis <mailto:lawson@kurrawong.ai>

## See Also

SHACL Playground implementation of owl2shacl based on topquadrant's open source API.

<https://shacl-play.sparna.fr/play/convert>

Why not just use this one?

I wanted control over the domain/range restrictions and also needed to include proper
messaging for the sh:properties so that fixing/reading validation errors is easier.

That implementation is more comprehensive than what I have done here, but for what I
need right now (2026-01-05) this doesn't matter.
