# [TEST003] Factory Pattern for Models (FactoryBoy)

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-02
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [TEST001]

## Description
Implement FactoryBoy factories for all models: easy test data generation, realistic fake data, override fields as needed.

## Acceptance Criteria
- [ ] Factory for each model (User, Warehouse, Product, etc.)
- [ ] Faker integration (realistic names, emails, GPS)
- [ ] SubFactory for relationships (Product → ProductFamily)
- [ ] Sequences for unique fields (email, serial numbers)
- [ ] Can override any field in tests

## Implementation
```python
import factory
from factory.faker import Faker
from app.models import User, Warehouse, Product

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None  # Set in conftest
        sqlalchemy_session_persistence = "commit"

    email = Faker('email')
    hashed_password = "$2b$12$..."
    role = "operator"
    is_active = True

class WarehouseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Warehouse

    name = Faker('company')
    code = factory.Sequence(lambda n: f"WH{n:03d}")
    geom = factory.LazyFunction(
        lambda: f"POLYGON(({random.uniform(-120,-100)} {random.uniform(30,40)}, ...))"
    )

class ProductFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Product

    name = Faker('word')
    sku = factory.Sequence(lambda n: f"SKU{n:05d}")
    family = factory.SubFactory(ProductFamilyFactory)
```

**Usage in tests:**
```python
def test_create_user(db_session):
    user = UserFactory.create(email="custom@example.com", role="admin")
    assert user.email == "custom@example.com"
    assert user.role == "admin"
```

## Testing
- Test factories create valid model instances
- Test factories respect field overrides
- Test SubFactory creates related objects

---
**Card Created**: 2025-10-09
