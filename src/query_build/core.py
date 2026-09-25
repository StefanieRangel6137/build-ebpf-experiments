"""Build and parse query strings with correct repeated-key handling.

Design decisions (stated plainly so the behaviour is unambiguous):

1. Repeated keys are ALWAYS collected into a list, even if there is only one
   value for that key. This is the only representation that survives a
   round-trip without loss, so it is used uniformly. A caller that wants a
   single value reads the first element explicitly.

2. Both keys and values are URL-encoded using urllib.parse.quote with the
   plus-sign left alone (plus is only space in application/x-www-form-urlencoded
   form bodies, NOT in the query string of a URL per RFC 3986). We encode space
   as %20 and never as '+'.

3. None values are rendered as a bare key with no '=': '?flag'. Empty-string
   values render as 'key='. This distinction matters for some servers.

4. Key order from insertion is preserved on build. On parse, order follows the
   first appearance of each key. Python dicts have guaranteed insertion order
   since 3.7, so we rely on it.

5. No third-party dependencies. Only urllib.parse from the standard library.
"""

from __future__ import annotations

from urllib.parse import quote, unquote, urlsplit, urlunsplit


class Query:
    """An ordered, multi-valued query-string container.

    Every key maps to a list of strings. Insertion order of keys is preserved.
    Repeated appends to the same key extend the list.
    """

    __slots__ = ("_data",)

    def __init__(self, initial=None):
        # Use a plain dict; insertion-ordered since Python 3.7.
        # Values are always list[str] so the internal invariant is simple.
        self._data = {}
        if initial:
            # Accept either a dict (which may already have list values or
            # scalars) or a list of (key, value) pairs.
            if isinstance(initial, dict):
                for k, v in initial.items():
                    if isinstance(v, (list, tuple)):
                        self._data[k] = [str(x) for x in v]
                    else:
                        self._data[k] = [str(v)]
            else:
                for k, v in initial:
                    self.add(k, v)

    def add(self, key, value):
        """Append value under key. key must be a string; value may be str or None."""
        if not isinstance(key, str):
            raise TypeError("key must be str, got %r" % type(key).__name__)
        if value is not None and not isinstance(value, str):
            raise TypeError("value must be str or None, got %r" % type(value).__name__)
        self._data.setdefault(key, []).append(value)

    def set(self, key, value):
        """Replace all values for key with a single value (str or None)."""
        if not isinstance(key, str):
            raise TypeError("key must be str, got %r" % type(key).__name__)
        if value is not None and not isinstance(value, str):
            raise TypeError("value must be str or None, got %r" % type(value).__name__)
        self._data[key] = [value]

    def get(self, key, default=None):
        """Return the first value for key, or default if the key is absent."""
        vals = self._data.get(key)
        if not vals:
            return default
        return vals[0]

    def get_all(self, key):
        """Return a copy of the list of all values for key."""
        return list(self._data.get(key, []))

    def keys(self):
        """Return keys in insertion order."""
        return list(self._data.keys())

    def items(self):
        """Yield (key, value) pairs, one per value, in order."""
        for k, vals in self._data.items():
            for v in vals:
                yield (k, v)

    def remove(self, key):
        """Delete all values for key. KeyError if absent."""
        del self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return sum(len(v) for v in self._data.values())

    def __eq__(self, other):
        if not isinstance(other, Query):
            return NotImplemented
        return self._data == other._data

    def __repr__(self):
        return "Query(%r)" % self._data

    def build(self):
        """Render this container as a query string WITHOUT a leading '?'."""
        return build(self)


def _encode_piece(s):
    # quote with safe='' so everything reserved gets encoded. We pass
    # encoding='utf-8' explicitly; str in py3 is already unicode so this is
    # just clarity. Spaces become %20, never '+'.
    return quote(s, safe='', encoding='utf-8')


def build(query):
    """Render a Query (or a list of (key,value) pairs) as a query string.

    Returns the query string WITHOUT a leading '?', so the caller can compose
    it into a URL or prepend '?' themselves. An empty Query yields ''.
    """
    if isinstance(query, Query):
        pairs = list(query.items())
    elif isinstance(query, dict):
        # Tolerate a plain dict; coerce values to lists like Query.__init__.
        pairs = []
        for k, v in query.items():
            if isinstance(v, (list, tuple)):
                for x in v:
                    pairs.append((k, x))
            else:
                pairs.append((k, v))
    else:
        pairs = list(query)

    parts = []
    for k, v in pairs:
        ek = _encode_piece(k)
        if v is None:
            parts.append(ek)
        else:
            parts.append(ek + "=" + _encode_piece(v))
    return "&".join(parts)


def parse(qs):
    """Parse a query string (with or without leading '?', or a full URL) into a Query.

    Splits on '&', then on the first '='. A piece with no '=' yields a None
    value. Values are URL-decoded with unquote, which treats '+' as space; this
    is a known compromise — see the README. Keys are always lists in the result.
    """
    if not qs:
        return Query()

    s = qs
    # Tolerate a full URL by taking only the query portion.
    if '#' in s or '/' in s or ':' in s:
        split = urlsplit(s)
        # If the string genuinely looks like a URL (has scheme or path), use
        # its query. Otherwise fall through and treat the whole thing as a
        # bare query string.
        if split.scheme or split.path or split.netloc:
            s = split.query
            if not s:
                # A URL with an empty query is still empty.
                return Query()
        # else: bare query that happens to contain ':' etc.

    if s.startswith('?'):
        s = s[1:]

    if not s:
        return Query()

    q = Query()
    for piece in s.split('&'):
        if not piece:
            continue
        if '=' in piece:
            k, _, v = piece.partition('=')
            q.add(unquote(k), unquote(v))
        else:
            q.add(unquote(piece), None)
    return q
