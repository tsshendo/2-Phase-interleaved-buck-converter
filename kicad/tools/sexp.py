"""Minimal S-expression reader/writer for KiCad files."""


class Sym(str):
    """Bare (unquoted) atom."""


def tokenize(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in '()':
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while s[j] != '"':
                if s[j] == '\\':
                    buf.append(s[j + 1])
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            yield ('S', ''.join(buf))
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()':
                j += 1
            yield Sym(s[i:j])
            i = j


def parse(s):
    stack = [[]]
    for t in tokenize(s):
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif isinstance(t, tuple):
            stack[-1].append(t[1])
        else:
            stack[-1].append(t)
    return stack[0]


def find(node, head):
    out = []
    if isinstance(node, list):
        if node and node[0] == head:
            out.append(node)
        for c in node:
            out += find(c, head)
    return out


def child(node, head):
    for c in node:
        if isinstance(c, list) and c and c[0] == head:
            return c
    return None


def quote(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def dump(node, indent=0):
    """Serialise a parsed node back to text (KiCad style tabs)."""
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return str(node)
        if isinstance(node, (int, float)):
            return fmt(node)
        return quote(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(dump(c) for c in node) + ')'
    parts = ['(' + dump(node[0])]
    i = 1
    while i < len(node) and not isinstance(node[i], list):
        parts[0] += ' ' + dump(node[i])
        i += 1
    for c in node[i:]:
        parts.append('\t' * (indent + 1) + dump(c, indent + 1))
    return '\n'.join(parts) + '\n' + '\t' * indent + ')'


def fmt(v):
    if isinstance(v, float):
        s = ('%.4f' % v).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(v)
