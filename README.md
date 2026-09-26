# query_build

Build and parse URL query strings with repeated keys handled correctly. Repeated keys are represented as a list under a single key, so round-tripping `tag=py&tag=web` does not collapse one of the values.

## Usage

```python
from query_build import Query, parse, build

q = Query()
q.add("tag", "py")
q.add("tag", "web")
q.set("page", "2")
print(build(q))          # tag=py&tag=web&page=2

parsed = parse("http://site/p?tag=py&tag=web")
print(parsed.get_all("tag"))  # ['py', 'web']
print(parsed.get("page", "1"))  # '1'
```

Exports: `Query`, `parse`, `build`.

## Why this exists

`urllib.parse` gives you `parse_qs`, which returns lists, and `urlencode`, which can encode lists — but the two disagree on ordering in edge cases, and `parse_qs` silently drops bare keys (a `?flag` with no `=` becomes an empty-string value, not a `None`). This library picks one consistent model: every key maps to a list, every value is either a string or `None`, and order is preserved on both build and parse.

The trade-off: callers must always ask for `get("key")` (first value) or `get_all("key")` (all values). There is no scalar shortcut, because a scalar shortcut is exactly what hides repeated keys.

## Edge you will hit

`parse` decodes `+` as space. That is correct for `application/x-www-form-urlencoded` bodies, and wrong for a bare URL query string per RFC 3986 — but real-world servers treat `+` as space in query strings often enough that decoding it is the least surprising choice. If you have a `+` that must survive round-trip, percent-encode it as `%2B` before building.

None values render as a bare key with no `=` (`flag`), empty strings render as `key=`. This distinction is preserved on round-trip.
