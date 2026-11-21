class QQNotebookExporterError(Exception):
    """Base error for the application."""


class AuthenticationRequiredError(QQNotebookExporterError):
    """Raised when a valid QQ Mail login session is not available."""


class QQMailAPIError(QQNotebookExporterError):
    """Raised when QQ Mail returns an invalid or unsuccessful response."""


class BrowserLaunchError(QQNotebookExporterError):
    """Raised when the browser or its persistent profile cannot be opened."""


class ExportError(QQNotebookExporterError):
    """Raised when one note cannot be written to disk."""
