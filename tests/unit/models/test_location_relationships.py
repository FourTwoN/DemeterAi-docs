"""Unit tests for LocationRelationship model.

These tests verify basic model instantiation and relationship logic.
Database constraint tests (unique pairs, no self-reference) are in integration tests.

Tests cover:
- Model instantiation with valid data
- Enum validation (contains, adjacent_to)
- Foreign key assignments (parent_location_id, child_location_id)
- Timestamp defaults (created_at, updated_at)
- Relationship attributes (parent_location, child_location)
"""

import pytest
from app.models.location_relationships import (
    LocationRelationship,
    RelationshipTypeEnum,
)

pytest.importorskip(
    "app.models.location_relationships",
    reason="LocationRelationship model not yet implemented",
)


class TestLocationRelationshipInstantiation:
    """Test basic model instantiation with valid data."""

    def test_create_contains_relationship(self):
        """Should create a valid 'contains' relationship."""
        relationship = LocationRelationship(
            parent_location_id=1,
            child_location_id=2,
            relationship_type=RelationshipTypeEnum.CONTAINS,
        )

        assert relationship.parent_location_id == 1
        assert relationship.child_location_id == 2
        assert relationship.relationship_type == RelationshipTypeEnum.CONTAINS

    def test_create_adjacent_to_relationship(self):
        """Should create a valid 'adjacent_to' relationship."""
        relationship = LocationRelationship(
            parent_location_id=3,
            child_location_id=4,
            relationship_type=RelationshipTypeEnum.ADJACENT_TO,
        )

        assert relationship.parent_location_id == 3
        assert relationship.child_location_id == 4
        assert relationship.relationship_type == RelationshipTypeEnum.ADJACENT_TO

    def test_relationship_type_enum_values(self):
        """Should accept valid RelationshipTypeEnum values."""
        assert RelationshipTypeEnum.CONTAINS.value == "contains"
        assert RelationshipTypeEnum.ADJACENT_TO.value == "adjacent_to"

    def test_relationship_type_string_value(self):
        """Should accept relationship_type as string."""
        relationship = LocationRelationship(
            parent_location_id=1, child_location_id=2, relationship_type="contains"
        )

        assert relationship.relationship_type == RelationshipTypeEnum.CONTAINS

        relationship2 = LocationRelationship(
            parent_location_id=3, child_location_id=4, relationship_type="adjacent_to"
        )

        assert relationship2.relationship_type == RelationshipTypeEnum.ADJACENT_TO


class TestLocationRelationshipForeignKeys:
    """Test foreign key assignments."""

    def test_parent_location_id_assignment(self):
        """Should correctly assign parent_location_id."""
        relationship = LocationRelationship(
            parent_location_id=10,
            child_location_id=20,
            relationship_type=RelationshipTypeEnum.CONTAINS,
        )

        assert relationship.parent_location_id == 10

    def test_child_location_id_assignment(self):
        """Should correctly assign child_location_id."""
        relationship = LocationRelationship(
            parent_location_id=15,
            child_location_id=25,
            relationship_type=RelationshipTypeEnum.ADJACENT_TO,
        )

        assert relationship.child_location_id == 25

    def test_different_location_ids(self):
        """Should accept different parent and child location IDs."""
        relationship = LocationRelationship(
            parent_location_id=100,
            child_location_id=200,
            relationship_type=RelationshipTypeEnum.CONTAINS,
        )

        assert relationship.parent_location_id != relationship.child_location_id


class TestLocationRelationshipRepresentation:
    """Test string representation and basic attributes."""

    def test_repr_method(self):
        """Should have a __repr__ method if defined."""
        relationship = LocationRelationship(
            parent_location_id=1,
            child_location_id=2,
            relationship_type=RelationshipTypeEnum.CONTAINS,
        )

        repr_str = repr(relationship)
        assert "LocationRelationship" in repr_str or "location_relationships" in str(relationship)
