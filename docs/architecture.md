## Current modeling simplification

For the initial prototype, reference catalogs are maintained in a single Python module and generated events include descriptive attributes.

In a production architecture, raw events would contain primarily identifiers and measurements. A separate enrichment layer would join device, subscriber, network cell, and application reference data before loading curated analytical datasets.