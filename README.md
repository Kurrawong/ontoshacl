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

See the `if __name__ == "__main__"` section at the bottom of
[ontoshacl.py](./ontoshacl.py) for configuration.

Basically, you just need to provide

- the path to the source ontology, a
- path to output the SHACL rules, and
- the metadata details for the validator.

To run it:

```bash
$ python ontoshacl.py
```

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
