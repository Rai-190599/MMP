# Integration Test Instructions — Marathon Management Platform Sprint 1

## End-to-End Flow Tests

These tests verify the full participant registration flow across all services.

### Full Registration + Login Flow
```bash
# 1. Register a new participant
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Runner",
    "email": "runner@test.com",
    "password": "testpass123",
    "role": "participant"
  }')

echo $REGISTER_RESPONSE | python3 -m json.tool
TOKEN=$(echo $REGISTER_RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. Login with same credentials
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "runner@test.com", "password": "testpass123"}' \
  | python3 -m json.tool

# 3. Attempt login with wrong password
curl -s -o /dev/null -w "Wrong password status: %{http_code}\n" \
  -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "runner@test.com", "password": "wrongpass"}'
```

### Database Verification
```bash
# Connect to postgres and verify tables exist
docker-compose exec postgres psql -U marathon -d marathon_db -c "\dt"
# Expected: users, events, registrations, notifications, tasks, volunteer_assignments

# Verify enums
docker-compose exec postgres psql -U marathon -d marathon_db -c "\dT+"
# Expected: user_role, registration_status, notification_channel, etc.

# Verify user was created
docker-compose exec postgres psql -U marathon -d marathon_db \
  -c "SELECT id, name, email, role FROM users;"
```

### Redis Connectivity
```bash
docker-compose exec redis redis-cli ping
# Expected: PONG
```

### MinIO Connectivity
```bash
curl -s http://localhost:9000/minio/health/live
# Expected: HTTP 200
# MinIO console: http://localhost:9001 (admin/password123)
```
