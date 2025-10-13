"""Local conftest for repository unit tests.

This module ensures test models are imported before the db_session fixture
creates tables, so Base.metadata includes test-specific models.
"""

# Import test models here so they register with Base.metadata
# This MUST be imported before any fixtures run
from tests.unit.repositories.test_base_repository import RepositoryTestModel  # noqa: F401
