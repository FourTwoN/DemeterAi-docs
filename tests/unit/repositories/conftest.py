"""Local conftest for repository unit tests.

This module ensures test models are imported before the db_session fixture
creates tables, so Base.metadata includes test-specific models.

Note: test_base_repository.py has been removed as it was obsolete.
No local imports needed here.
"""

# Test models have been removed - no local imports needed
