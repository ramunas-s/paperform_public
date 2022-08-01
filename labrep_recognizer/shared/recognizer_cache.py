import pickle

import cachetools

from labrep_recognizer.shared.utils import make_dirs


class RecognizerCache(dict):
    def __init__(self, cache_file, persist_interval=10):
        self._cache_file = cache_file
        self._persist_interval = persist_interval
        self._persist_counter = persist_interval
        try:
            with open(self._cache_file, "rb") as f:
                super().__init__(pickle.load(f))
        except FileNotFoundError:
            super().__init__()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._persist_cache_on_interval()

    def _persist_cache_on_interval(self):
        self._persist_counter -= 1
        if self._persist_counter <= 0:
            self.persist_cache()
            self._persist_counter = self._persist_interval

    def persist_cache(self):
        make_dirs(self._cache_file)
        with open(self._cache_file, "wb") as f:
            pickle.dump(dict(self), f)

    def pickled_hashkey(*args, **kwargs):
        pickled_args = pickle.dumps(args)
        pickled_kwargs = pickle.dumps(kwargs)
        return cachetools.keys.hashkey(pickled_args, pickled_kwargs)
