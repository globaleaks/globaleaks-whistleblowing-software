from collections import OrderedDict

class LRUCache(OrderedDict):
    def __init__(self, max_size=1000, *args, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        # Move key to the end to mark as recently accessed
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            # Remove it first to re-insert and move to end
            del self[key]
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            # Pop the least recently used item (leftmost)
            self.popitem(last=False)
