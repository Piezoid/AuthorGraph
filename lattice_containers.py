from collections import defaultdict

dict_keys = type(dict().keys())
def norm_to_set(x):
    """Normalize an iterable object (dict, set, DeduplicatedSet, list, etc) to
    an object supporting set operations (dict_keys, set).
    """
    if isinstance(x, (set, dict_keys)):
        return x
    elif isinstance(x, (dict, DeduplicatedSet)):
        return x.keys()
    else:
        return set(x)

class DeduplicatedSet:
    """A set with values on a lattice.
    Two keys may be equal but contains different quantity of information.
    add() will call __ior__ on the existing keys to augment its information content.
    Once a key is fisrt defined in the set, it will never be replaced, but may be updated.
    (ie. its id() never change)
    """
    def __init__(self, values=None):
        self._keys = dict()
        if values:
            self.update(values)

    def __contains__(self, key):
        return self._keys.__contains__(key)

    def __len__(self):
        return len(self._keys)

    def __iter__(self):
        return iter(self._keys)

    def keys(self):
        return self._keys.keys()

    def get_dedupkey(self, k, or_set=False, default=None):
        kfound = self._keys.get(k)
        if kfound is None:
            if or_set:
                self._keys[k] = k
                kfound = k
            else:
                return default
        if k is not kfound:
            merge = getattr(kfound, '__ior__', None)
            if merge is not None:
                merge(k)
        return kfound

    def add(self, key):
        return self.get_dedupkey(k, or_set=True)

    def remove(self, key):
        return self._keys.pop(self, key)

    def update(self, other):
        keys = []
        for k in other:
            keys.append(self.get_dedupkey(k, or_set=True))
        return keys

    def __ior__(self, other):
        for k in other:
            self.get_dedupkey(k, or_set=True)
        return self

    intersection = lambda self, other: self._keys.keys() & norm_to_set(other)
    __and__ = intersection
    __rand__ = intersection

    #union = lambda self, other: self._keys.keys() | norm_to_set(other)
    #__or__ = union
    #__ror__ = union

    difference = lambda self, other: self._keys.keys() - norm_to_set(other)
    __sub__ = difference
    __rsub__ = lambda self, other: norm_to_set(other) - self._keys.keys()

class DeduplicatedKeysDict(DeduplicatedSet):
    """A dictionary with DeduplicatedSet keys
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._values = dict()

    def get(self, k, default=None):
        dedupkey = self.get_dedupkey(k)
        if dedupkey is None:
            return default
        else:
            return self._values[id(dedupkey)]

    def __getitem__(self, k):
        dedupkey = self.get_dedupkey(k)
        if dedupkey is None:
            raise KeyError(k)
        else:
            return self._values[id(dedupkey)]

    def __setitem__(self, k, item):
        dedupkey = self.get_dedupkey(k, or_set=True)
        self._values[id(dedupkey)] = item

    def values(self):
        return self._values.values()

    def items(self):
        for k in self._keys:
            yield k, self._values[id(k)]

    def update(self, items):
        if isinstance(items, (DeduplicatedKeysDict, dict)):
            items = items.items()

        dedupkeys = []
        for k, v in items:
            dedupkey = self.get_dedupkey(k, or_set=True)
            dedupkeys.append(dedupkey)
            self._values[id(dedupkey)] = v

        return dedupkeys


class DeduplicatedKeysDefaultDict(DeduplicatedKeysDict):
    "Like default dict but with DeduplicatedKeysDict's semantics."
    def __init__(self, factory, **kwargs):
        DeduplicatedSet.__init__(self, **kwargs)
        self._values = defaultdict(factory)

    def __getitem__(self, k):
        dedupkey = self.get_dedupkey(k, or_set=True)
        return self._values[id(dedupkey)]


class DeduplicatedKeysDictOfSets(DeduplicatedKeysDefaultDict):
    """A specialized version of DeduplicatedKeysDefaultDict with set values.
    Updating compute the union of the values where the keys intersects.
    """
    def __init__(self, **kwargs):
        super().__init__(set, **kwargs)

    def __setitem__(self, k, item):
        dedupkey = self.get_dedupkey(k, or_set=True)
        if type(item) is set:
            self._values[id(dedupkey)] |= item
        else:
            self._values[id(dedupkey)].add(item)

    def update(self, items):
        if isinstance(items, (DeduplicatedKeysDict, dict)):
            items = items.items()

        dedupkeys = []
        for k, v in items:
            dedupkey = self.get_dedupkey(k, or_set=True)
            dedupkeys.append(dedupkey)
            if type(v) is set:
                self._values[id(dedupkey)] |= v
            else:
                self._values[id(dedupkey)].add(v)
        return dedupkeys
