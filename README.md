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

## Status

The script has been significantly enhanced to handle comprehensive OWL to SHACL conversion. It has been tested with:

- **RiC-O ontology**: The original test case with qualified cardinality restrictions
- **Comprehensive test ontology**: Includes all major OWL restriction types

### Known Limitations

While the script now handles most common OWL restriction types, there are some advanced features that could be added:

- **Complex class expressions**: Currently handles `owl:unionOf`, but could be extended to support `owl:intersectionOf`, `owl:complementOf`, etc.
- **Property chains**: Could handle `owl:propertyChainAxiom` for complex property paths
- **Datatype restrictions**: Could add more sophisticated handling of datatype restrictions
- **Advanced cardinality**: Could handle more complex cardinality expressions

Contributions to extend these capabilities are welcome!

### Implementation status

The enhanced script now supports comprehensive OWL to SHACL conversion:

| OWL Restriction Type          | SHACL Equivalent                     | Status         |
| ----------------------------- | ------------------------------------ | -------------- |
| rdfs:range                    | sh:class                             | ✅ Implemented |
| owl:onClass                   | sh:class                             | ✅ Implemented |
| owl:minQualifiedCardinality   | sh:minCount + sh:class               | ✅ Implemented |
| owl:maxQualifiedCardinality   | sh:maxCount + sh:class               | ✅ Implemented |
| owl:qualifiedCardinality      | sh:minCount + sh:maxCount + sh:class | ✅ Implemented |
| owl:minCardinality            | sh:minCount                          | ✅ Implemented |
| owl:maxCardinality            | sh:maxCount                          | ✅ Implemented |
| owl:cardinality               | sh:minCount + sh:maxCount            | ✅ Implemented |
| owl:someValuesFrom            | sh:class                             | ✅ Implemented |
| owl:allValuesFrom             | sh:class                             | ✅ Implemented |
| owl:hasValue                  | sh:hasValue                          | ✅ Implemented |
| owl:unionOf (in restrictions) | sh:or                                | ✅ Implemented |

### Features

- **Comprehensive OWL restriction handling**: Converts all common OWL restriction types to their SHACL equivalents
- **Complex class expressions**: Handles union classes (`owl:unionOf`) in restrictions and converts them to `sh:or`
- **Qualified and unqualified cardinality**: Supports both qualified (with class restrictions) and unqualified cardinality restrictions
- **Value restrictions**: Converts `owl:someValuesFrom`, `owl:allValuesFrom`, and `owl:hasValue` restrictions
- **Helpful error messages**: Automatically generates descriptive validation messages for each SHACL constraint
- **Configurable severity**: Domain/range restrictions can be included with configurable severity levels
- **Validator metadata**: Includes comprehensive ontology metadata for the generated validator

### OWL to SHACL Mapping Details

1. **Existential Restrictions** (`owl:someValuesFrom`)
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:someValuesFrom SomeClass ]`
   - SHACL: `sh:property [ sh:path prop; sh:class SomeClass ]`

2. **Universal Restrictions** (`owl:allValuesFrom`)
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:allValuesFrom SomeClass ]`
   - SHACL: `sh:property [ sh:path prop; sh:class SomeClass ]`

3. **Value Restrictions** (`owl:hasValue`)
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:hasValue specificInstance ]`
   - SHACL: `sh:property [ sh:path prop; sh:hasValue specificInstance ]`

4. **Qualified Cardinality Restrictions**
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:onClass SomeClass; owl:minQualifiedCardinality "1" ]`
   - SHACL: `sh:property [ sh:path prop; sh:class SomeClass; sh:minCount 1 ]`

5. **Unqualified Cardinality Restrictions**
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:minCardinality "1" ]`
   - SHACL: `sh:property [ sh:path prop; sh:minCount 1 ]`

6. **Complex Class Expressions**
   - OWL: `Class rdfs:subClassOf [ owl:onProperty prop; owl:someValuesFrom [ owl:unionOf (Class1 Class2) ] ]`
   - SHACL: `sh:property [ sh:path prop; sh:or ( [sh:class Class1] [sh:class Class2] ) ]`

See the full table at <https://spinrdf.org/shacl-and-owl.html> for more details on OWL-SHACL mappings.

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
