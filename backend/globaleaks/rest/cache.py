from collections import OrderedDict
from threading import RLock


class Cache:
    # Tune these safely
    MAX_ENTRIES_PER_TENANT = 256

    # tid -> OrderedDict[(resource, language)] = (content_type, data)
    _tenants = {}
    _lock = RLock()

    @classmethod
    def get(cls, tid, resource, language):
        key = (resource, language)

        with cls._lock:
            tenant_cache = cls._tenants.get(tid)
            if not tenant_cache:
                return None

            try:
                value = tenant_cache.pop(key)
                # mark as most recently used
                tenant_cache[key] = value
                return value
            except KeyError:
                return None

    @classmethod
    def set(cls, tid, resource, language, content_type, data):
        key = (resource, language)
        value = (content_type, data)

        with cls._lock:
            tenant_cache = cls._tenants.get(tid)

            if tenant_cache is None:
                tenant_cache = OrderedDict()
                cls._tenants[tid] = tenant_cache

            # refresh if already present
            tenant_cache.pop(key, None)
            tenant_cache[key] = value

            # LRU eviction per tenant
            while len(tenant_cache) > cls.MAX_ENTRIES_PER_TENANT:
                tenant_cache.popitem(last=False)

        return value

    @classmethod
    def invalidate(cls, tid=1):
        with cls._lock:
            if tid == 1:
                # global flush (root tenant semantics preserved)
                cls._tenants.clear()
            else:
                cls._tenants.pop(tid, None)
