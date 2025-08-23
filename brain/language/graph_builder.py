"""
Pablo Language — Graph core + .pgraph codec (v0.1, language-only)

Provides:
- 8·8·8 data shapes (Node, Edge, Graph) for WRITING profile
- GraphBuilder (add_node / add_edge / finalize)
- Base-128 varint encode/decode helpers
- encode_pgraph(Graph) -> bytes
- decode_pgraph(bytes) -> Graph

Notes
- Language-only: no Code/Math node/edge types included.
- Strings are not stored inline; use integer IDs (dictionary-encoded) for label_id, etc.
- LOUDS/CSR and block writer/reader can come next as separate modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple, Optional


# ---------------------------
# Enums / Flags (language-only)
# ---------------------------

class GraphType(IntEnum):
    SIMPLE = 1
    MULTI = 2
    TREE = 3
    DAG = 4
    HETERO = 5
    TEMPORAL = 6


class SchemaID(IntEnum):
    WRITING = 1  # language graphs only for now


class NodeType(IntEnum):
    TOKEN = 1
    ENTITY = 2
    PREDICATE = 3
    EVENT = 4
    PHRASE = 5
    EDU = 6
    DISCOURSE_REL = 7
    NEGATION = 8
    MODALITY = 9
    QUANTIFIER = 10
    TIME_EXPR = 11
    PLACE = 12
    KG_ENTITY = 13
    KG_CONCEPT = 14
    # (no CODE_NODE / MATH_NODE here)


class EdgeType(IntEnum):
    DEP = 1
    ROLE = 2
    COREF = 3
    DISCOURSE = 4
    SCOPES_OVER = 5
    HAPPENS_AT = 6
    LOCATED_IN = 7
    SAME_AS = 8
    NEXT = 9
    PUNCT = 10
    ARG_OF = 11
    # (no AST_CHILD / CFG_NEXT / DATA_FLOW / EQUALS / REWRITES_TO here)


# 16-bit node flags (bit positions)
NF_IS_ROOT        = 1 << 0
NF_IS_STOP        = 1 << 1
NF_IS_CAPITALIZED = 1 << 2
NF_IS_PUNCT       = 1 << 3
NF_PROPOSED       = 1 << 4
NF_IS_HEAD        = 1 << 5
NF_SENT_END_STRONG = 1 << 6  # new: ., ?, !
NF_SENT_END_WEAK   = 1 << 7  # new: closers after end, or ellipsis
# (reserve remaining bits for future use)

# 16-bit edge flags (bit positions)
EF_DIRECTED   = 1 << 0
EF_PROPOSED   = 1 << 1
EF_SYMMETRIC  = 1 << 2
EF_CROSS_SENT = 1 << 3
EF_NEGATED    = 1 << 4
EF_INFERRED   = 1 << 5
# (reserve remaining bits)


# ---------------------------
# Core data shapes (8·8·8)
# ---------------------------

Span = Tuple[int, int]  # [start, end) token or char range (generic for now)

@dataclass
class Node:
    node_id: int                  # varint
    n_type: int                   # uint8 (NodeType)
    sub_type: int                 # uint8 (POS id, frame id, etc.)
    features_ref: int             # varint (0 = none)
    span: Span                    # tuple varints (start, end)
    flags: int                    # uint16
    confidence: int               # uint8 (0..255)
    label_id: int                 # varint (lemma/entity/class id)


@dataclass
class Edge:
    src_id: int                   # varint
    dst_id: int                   # varint
    e_type: int                   # uint8 (EdgeType)
    weight: int                   # uint8 (0..255; 255 = max)
    time: int                     # varint (0 if unused)
    flags: int                    # uint16
    confidence: int               # uint8
    attr_ref: int                 # varint (dep_label id, role id, etc.)


@dataclass
class Graph:
    graph_id: int                 # varint or 64-bit hash (we use int)
    graph_type: int               # uint8 (GraphType)
    num_nodes: int                # varint
    num_edges: int                # varint
    g_features: Optional[bytes]   # optional int8[64|128] thumbnail
    source_id: int                # varint
    version: int                  # varint (schema/build or epoch)
    schema_id: int                # uint8 (SchemaID)
    nodes: List[Node]
    edges: List[Edge]


# ---------------------------
# Varint utilities (unsigned)
# ---------------------------

def _uvarint_encode(value: int) -> bytes:
    """Unsigned base-128 varint (LEB128-style)."""
    if value < 0:
        raise ValueError("uvarint cannot encode negative values")
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _uvarint_decode(buf: bytes, offset: int = 0) -> Tuple[int, int]:
    """Returns (value, new_offset)."""
    shift = 0
    value = 0
    i = offset
    while True:
        if i >= len(buf):
            raise ValueError("uvarint: truncated input")
        b = buf[i]
        i += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 63:  # sanity for huge ints
            raise ValueError("uvarint: value too large")
    return value, i


# ---------------------------
# GraphBuilder
# ---------------------------

class GraphBuilder:
    """
    Minimal graph builder for language graphs.
    Add nodes/edges, then call finalize() to get an immutable Graph.
    """
    __slots__ = ("_graph_id", "_graph_type", "_source_id", "_version",
                 "_schema_id", "_nodes", "_edges", "_features")

    def __init__(self,
                 graph_id: int,
                 schema_id: int = SchemaID.WRITING,
                 graph_type: int = GraphType.HETERO,
                 source_id: int = 0,
                 version: int = 1,
                 g_features: Optional[bytes] = None) -> None:
        self._graph_id = int(graph_id)
        self._schema_id = int(schema_id)
        self._graph_type = int(graph_type)
        self._source_id = int(source_id)
        self._version = int(version)
        self._features = g_features
        self._nodes: List[Node] = []
        self._edges: List[Edge] = []

    # Node API
    def add_node(self,
                 n_type: int,
                 sub_type: int,
                 label_id: int,
                 span: Span,
                 *,
                 flags: int = 0,
                 confidence: int = 255,
                 features_ref: int = 0) -> int:
        node_id = len(self._nodes)
        self._nodes.append(Node(
            node_id=node_id,
            n_type=int(n_type),
            sub_type=int(sub_type),
            features_ref=int(features_ref),
            span=(int(span[0]), int(span[1])),
            flags=int(flags),
            confidence=int(confidence),
            label_id=int(label_id),
        ))
        return node_id

    # Edge API
    def add_edge(self,
                 src_id: int,
                 dst_id: int,
                 e_type: int,
                 *,
                 weight: int = 255,
                 time: int = 0,
                 flags: int = EF_DIRECTED,
                 confidence: int = 255,
                 attr_ref: int = 0) -> int:
        self._edges.append(Edge(
            src_id=int(src_id),
            dst_id=int(dst_id),
            e_type=int(e_type),
            weight=int(weight),
            time=int(time),
            flags=int(flags),
            confidence=int(confidence),
            attr_ref=int(attr_ref),
        ))
        return len(self._edges) - 1

    def set_thumbnail(self, features: Optional[bytes]) -> None:
        if features is not None and len(features) not in (64, 128):
            raise ValueError("g_features must be 64 or 128 bytes (int8) or None")
        self._features = features

    def finalize(self) -> Graph:
        return Graph(
            graph_id=self._graph_id,
            graph_type=self._graph_type,
            num_nodes=len(self._nodes),
            num_edges=len(self._edges),
            g_features=self._features,
            source_id=self._source_id,
            version=self._version,
            schema_id=self._schema_id,
            nodes=list(self._nodes),
            edges=list(self._edges),
        )


# ---------------------------
# .pgraph codec (single graph)
# ---------------------------

_PG_MAGIC = b"PGRA"  # single-graph payload wrapper

def encode_pgraph(g: Graph) -> bytes:
    """
    Encode a single Graph to bytes.
    Layout:
      magic[4]
      Graph(8) fields (except features length placed in adjuncts)
      nodes[]
      edges[]
      adjuncts:
        g_features_len (varint: 0, 64 or 128) + raw bytes (if any)
    """
    out = bytearray()
    out += _PG_MAGIC

    # Graph header
    out += _uvarint_encode(g.graph_id)
    out.append(int(g.graph_type) & 0xFF)
    out += _uvarint_encode(g.num_nodes)
    out += _uvarint_encode(g.num_edges)
    out += _uvarint_encode(g.source_id)
    out += _uvarint_encode(g.version)
    out.append(int(g.schema_id) & 0xFF)

    # Node table
    for n in g.nodes:
        out += _uvarint_encode(n.node_id)
        out.append(n.n_type & 0xFF)
        out.append(n.sub_type & 0xFF)
        out += _uvarint_encode(n.features_ref)
        out += _uvarint_encode(n.span[0])
        out += _uvarint_encode(n.span[1])
        out += (n.flags & 0xFFFF).to_bytes(2, "little")
        out.append(n.confidence & 0xFF)
        out += _uvarint_encode(n.label_id)

    # Edge table
    for e in g.edges:
        out += _uvarint_encode(e.src_id)
        out += _uvarint_encode(e.dst_id)
        out.append(e.e_type & 0xFF)
        out.append(e.weight & 0xFF)
        out += _uvarint_encode(e.time)
        out += (e.flags & 0xFFFF).to_bytes(2, "little")
        out.append(e.confidence & 0xFF)
        out += _uvarint_encode(e.attr_ref)

    # Adjuncts: g_features
    feat = g.g_features or b""
    out += _uvarint_encode(len(feat))
    if feat:
        out += feat
    return bytes(out)


def decode_pgraph(buf: bytes) -> Graph:
    """Decode a single Graph from bytes produced by encode_pgraph()."""
    i = 0
    if buf[:4] != _PG_MAGIC:
        raise ValueError("Invalid magic; not a .pgraph single-graph payload")
    i = 4

    graph_id, i = _uvarint_decode(buf, i)
    graph_type = buf[i]; i += 1
    num_nodes, i = _uvarint_decode(buf, i)
    num_edges, i = _uvarint_decode(buf, i)

    source_id, i = _uvarint_decode(buf, i)
    version, i = _uvarint_decode(buf, i)
    schema_id = buf[i]; i += 1

    nodes: List[Node] = []
    for _ in range(num_nodes):
        node_id, i = _uvarint_decode(buf, i)
        n_type = buf[i]; i += 1
        sub_type = buf[i]; i += 1
        features_ref, i = _uvarint_decode(buf, i)
        span0, i = _uvarint_decode(buf, i)
        span1, i = _uvarint_decode(buf, i)
        flags = int.from_bytes(buf[i:i+2], "little"); i += 2
        confidence = buf[i]; i += 1
        label_id, i = _uvarint_decode(buf, i)
        nodes.append(Node(
            node_id=node_id,
            n_type=n_type,
            sub_type=sub_type,
            features_ref=features_ref,
            span=(span0, span1),
            flags=flags,
            confidence=confidence,
            label_id=label_id,
        ))

    edges: List[Edge] = []
    for _ in range(num_edges):
        src_id, i = _uvarint_decode(buf, i)
        dst_id, i = _uvarint_decode(buf, i)
        e_type = buf[i]; i += 1
        weight = buf[i]; i += 1
        time, i = _uvarint_decode(buf, i)
        flags = int.from_bytes(buf[i:i+2], "little"); i += 2
        confidence = buf[i]; i += 1
        attr_ref, i = _uvarint_decode(buf, i)
        edges.append(Edge(
            src_id=src_id,
            dst_id=dst_id,
            e_type=e_type,
            weight=weight,
            time=time,
            flags=flags,
            confidence=confidence,
            attr_ref=attr_ref,
        ))

    feat_len, i = _uvarint_decode(buf, i)
    if feat_len:
        g_features = buf[i:i+feat_len]
        if len(g_features) != feat_len:
            raise ValueError("Truncated g_features")
        i += feat_len
    else:
        g_features = None

    return Graph(
        graph_id=graph_id,
        graph_type=graph_type,
        num_nodes=len(nodes),
        num_edges=len(edges),
        g_features=g_features,
        source_id=source_id,
        version=version,
        schema_id=schema_id,
        nodes=nodes,
        edges=edges,
    )


# ---------------------------
# Tiny self-check (manual)
# ---------------------------

def _self_check() -> None:
    gb = GraphBuilder(graph_id=1, schema_id=SchemaID.WRITING, graph_type=GraphType.HETERO)
    t1 = gb.add_node(NodeType.TOKEN, sub_type=0, label_id=123, span=(0, 1),
                     flags=NF_IS_CAPITALIZED, confidence=240)
    t2 = gb.add_node(NodeType.TOKEN, sub_type=0, label_id=456, span=(1, 2))
    gb.add_edge(t1, t2, EdgeType.NEXT)
    g = gb.finalize()

    blob = encode_pgraph(g)
    g2 = decode_pgraph(blob)

    assert g2.graph_id == g.graph_id
    assert g2.num_nodes == 2 and g2.num_edges == 1
    assert g2.nodes[0].label_id == 123
    assert g2.edges[0].src_id == 0 and g2.edges[0].dst_id == 1


if __name__ == "__main__":
    _self_check()
    print("graph_builder (language-only): OK")
