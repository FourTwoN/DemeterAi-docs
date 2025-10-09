# [TEST010] Mock External Services (S3, Redis)

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-02
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocks [TEST009]

## Description
Mock external services for testing: S3 (moto), Redis (fakeredis). Tests run without real AWS or Redis.

## Acceptance Criteria
- [ ] Mock S3 with moto library
- [ ] Mock Redis with fakeredis
- [ ] Tests run without AWS credentials
- [ ] Tests run without Redis server
- [ ] Mock supports all operations used in code

## Implementation
```python
import pytest
from moto import mock_s3
import fakeredis

@pytest.fixture
def mock_s3_client():
    with mock_s3():
        import boto3
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='demeterai-photos')
        yield s3

@pytest.fixture
def mock_redis_client():
    return fakeredis.FakeRedis()

def test_s3_upload(mock_s3_client):
    """Test S3 upload without real AWS."""
    mock_s3_client.upload_file(
        'test_photo.jpg',
        'demeterai-photos',
        'original/2025/10/09/test.jpg'
    )

    # Verify uploaded
    response = mock_s3_client.list_objects_v2(
        Bucket='demeterai-photos',
        Prefix='original/'
    )
    assert len(response['Contents']) == 1

def test_redis_cache(mock_redis_client):
    """Test Redis caching without real Redis server."""
    mock_redis_client.set('key', 'value', ex=300)
    assert mock_redis_client.get('key') == b'value'

    # Test expiration
    import time
    mock_redis_client.set('key2', 'value2', ex=1)
    time.sleep(2)
    assert mock_redis_client.get('key2') is None
```

## Testing
- Verify mocks work like real services
- Test all S3 operations used (upload, download, delete)
- Test all Redis operations (set, get, delete, expire)
- Verify tests run fast without network

---
**Card Created**: 2025-10-09
