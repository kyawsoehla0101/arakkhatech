from whitenoise.storage import CompressedManifestStaticFilesStorage


class TolerantCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Subclass of whitenoise's CompressedManifestStaticFilesStorage that,
    when a static file is missing from the manifest (e.g. a new file was
    added and collectstatic hasn't been re-run yet), returns the original
    unhashed URL instead of raising ValueError.

    This prevents 500 errors on DEBUG=False whenever new static assets
    are deployed without running collectstatic immediately afterwards.
    """

    def stored_name(self, name):
        try:
            return super().stored_name(name)
        except ValueError:
            parsed_name = self.clean_name(name)
            self.hashed_files[name] = parsed_name
            return parsed_name
