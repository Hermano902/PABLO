from brain.language.tokenizer import tokenize, tokens_to_graph
from brain.language.morph import Vocab, analyze_tokens, annotate_graph

text = "Are you okay?"
toks = tokenize(text)
g = tokens_to_graph(text)
v = Vocab()
m = analyze_tokens(toks, v)
annotate_graph(g, toks, m)
# g.nodes[i].label_id and g.nodes[i].sub_type are now set
