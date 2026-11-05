class BundleError(Exception):
    """A sanitized, stable application error; never contains native diagnostics."""

    def __init__(self, code, *, count=None):
        self.code = code
        self.count = count
        super().__init__(code)

    def as_dict(self):
        result = {"code": self.code}
        if self.count is not None:
            result["count"] = self.count
        return result
