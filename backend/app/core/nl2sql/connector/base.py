"""Abstract base class for database connectors."""

from abc import ABC, abstractmethod
from typing import List

from app.schemas.nl2sql import DbConfigTestResponse


class DatabaseConnector(ABC):
    """Base class for database-specific connectors.

    Each implementation handles a single database dialect, providing
    connection testing, table/column listing, and connection URL building.
    """

    @property
    @abstractmethod
    def db_type(self) -> str:
        """Database type identifier (e.g. 'mysql', 'postgresql')."""

    @property
    def default_port(self) -> int:
        """Default port for this database type."""
        return 0

    @abstractmethod
    def test_connection(self, host: str, port: int, database: str,
                        username: str, password: str,
                        schema: str = "", extra_params: str = "",
                        ) -> DbConfigTestResponse:
        """Test a database connection.

        Returns:
            DbConfigTestResponse with success/failure and latency.
        """

    @abstractmethod
    def get_tables(self, host: str, port: int, database: str,
                   username: str, password: str,
                   schema: str = "", extra_params: str = "",
                   ) -> List[dict]:
        """Get all tables from the database.

        Returns:
            List of dicts with keys: table_name, table_comment.
        """

    @abstractmethod
    def get_columns(self, host: str, port: int, database: str,
                    username: str, password: str,
                    table_name: str,
                    schema: str = "", extra_params: str = "",
                    ) -> List[dict]:
        """Get columns for a specific table.

        Returns:
            List of dicts with keys: column_name, column_type,
            column_comment, is_primary_key, is_nullable.
        """

    @abstractmethod
    def build_connection_url(self, host: str, port: int, database: str,
                             username: str, password: str,
                             schema: str = "", extra_params: str = "",
                             ) -> str:
        """Build a SQLAlchemy connection URL for this database."""
