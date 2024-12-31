class Downloader:

    def download(self, url, destination):
        """
        Download a file from the given URL to the specified destination.

        Args:
            url (str): The file URL to download.
            destination (str): The local file path to save the downloaded file.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the `download` method.")
