# Performance Tests

This directory contains performance and load testing for the AIOps Agent system.

## Test Categories

### 1. Load Testing (`test_load.py`)
**Purpose**: Validate system performance under expected production load.

**What it tests**:
- Throughput (requests/second)
- Latency percentiles (p50, p95, p99)
- Error rates under normal concurrent load
- System stability under expected traffic

**Configuration**:
- 10 concurrent users
- 50 total requests
- Expected p95 latency: < 120s
- Max error rate: 1%

**Run**:
```bash
pytest tests/performance/test_load.py -v
```

### 2. Stress Testing (`test_stress.py`)
**Purpose**: Find the breaking point and maximum capacity.

**What it tests**:
- Gradual load increase (5, 10, 15, 20 concurrent users)
- System behavior beyond normal capacity
- Graceful degradation
- Recovery after overload
- Spike handling (sudden traffic burst)

**Run**:
```bash
pytest tests/performance/test_stress.py -v -m slow
```

### 3. Soak Testing (`test_soak.py`)
**Purpose**: Long-running stability test to detect issues over time.

**What it tests**:
- Memory leaks
- Resource exhaustion
- Performance degradation over time
- Connection pool stability

**Configuration**:
- Duration: 5 minutes (300 seconds)
- 3 concurrent users
- ~1 request/second rate

**Run**:
```bash
pytest tests/performance/test_soak.py -v -m soak
```

## Quick Start

### Run All Performance Tests
```bash
pytest tests/performance/ -v
```

### Run Only Fast Tests (exclude soak)
```bash
pytest tests/performance/ -v -m "not soak"
```

### Run Only Slow/Long Tests
```bash
pytest tests/performance/ -v -m slow
```

## Understanding Results

### Load Test Output
```
📊 Load Test Results:
  Total Duration: 45.23s
  Throughput: 1.10 req/s
  Success Rate: 100.0%
  Error Rate: 0.0%

  Latency Metrics:
    p50: 8.45s
    p95: 15.32s
    p99: 18.67s
    avg: 9.12s
```

**What to look for**:
- ✅ p95 latency < 120s
- ✅ Error rate < 1%
- ✅ Throughput meets requirements

### Stress Test Output
```
📊 Stress Test Summary:
  5 users: 100.0% success, 0.85 req/s, p95: 12.34s
  10 users: 98.0% success, 1.45 req/s, p95: 18.56s
  15 users: 92.0% success, 1.89 req/s, p95: 25.78s
  20 users: 75.0% success, 2.01 req/s, p95: 45.23s

⚠️  Breaking point reached at 20 concurrent users
```

**What to look for**:
- System handles baseline load (5-10 users) with >95% success
- Identify saturation point (where success rate drops)
- Note maximum throughput achieved

### Soak Test Output
```
📊 Performance Over Time (30s windows):
  Window | Requests | Success% | Avg Latency | p95 Latency
  ---------------------------------------------------------------
       0 |       28 |   100.0% |       8.45s |      12.34s
       1 |       31 |   100.0% |       8.67s |      12.89s
       2 |       29 |   100.0% |       8.52s |      12.45s
       ...

  Performance Degradation:
    First Window Latency: 8.45s
    Last Window Latency: 8.78s
    Degradation: +3.9%
```

**What to look for**:
- ✅ Degradation < 20% (no memory leaks)
- ✅ Consistent success rate across windows
- ✅ Stable latency over time

## Performance Benchmarking vs Testing

**Performance Tests** (this directory):
- Pytest-based
- Validates SLA compliance
- Part of CI/CD pipeline
- Pass/fail assertions

**Benchmark Script** (`scripts/benchmark.py`):
- Standalone profiling tool
- Generates detailed reports
- Used for optimization
- No pass/fail (measurement only)

## Monitoring During Tests

While tests run, monitor:

### Prometheus Metrics
```bash
# View all service metrics
curl http://localhost:8000/metrics
curl http://localhost:8005/metrics
```

### Service Health
```bash
# Check service mesh health
curl http://localhost:8000/health/mesh | jq
```

### Container Resources
```bash
# Monitor resource usage
docker stats
```

## Troubleshooting

### Tests Timing Out
- Increase timeout in test configuration
- Check if services are healthy
- Verify network connectivity

### High Error Rates
- Check service logs: `docker logs aiops-agent-monitor`
- Verify circuit breakers aren't tripping
- Check resource constraints

### Inconsistent Results
- Ensure system is idle before testing
- Clear caches/restart services
- Run tests multiple times for baseline

## Best Practices

1. **Run on isolated environment**: Don't run performance tests on production
2. **Warm up first**: Run a few requests before measuring
3. **Monitor resources**: Watch CPU, memory, connections
4. **Baseline first**: Establish baseline before optimizations
5. **Repeat tests**: Run multiple times for statistical significance

## Next Steps

After running performance tests:

1. **Identify bottlenecks**: Use metrics to find slow services
2. **Optimize**: Scale services, tune queries, add caching
3. **Re-test**: Validate improvements
4. **Document**: Record baseline and improvements
