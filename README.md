# Graph Summary of Ontology-based Annotation

SObA renders ontology-based annotations as a pruned directed acyclic graph. Every
node carries annotations — some directly, others by inference up the ontology's
transitive closure (`regulates_closure`: `is_a`, `part_of`, and `regulates`). The
graph keeps the minimal set of relationships connecting those terms (LCA node
selection + transitive-reduction of edges).

- **Front end:** Cytoscape.js graph embedded in gene-page widgets.
- **Back end:** SOLR server (ontology + annotation data) + CGI (`soba.cgi`:
  processing + JSONP API).
