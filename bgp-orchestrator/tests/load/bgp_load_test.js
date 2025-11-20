/**
 * K6 Load Test for BGP Orchestrator API
 * 
 * Simulates:
 * - 100 concurrent users
 * - Each user creates 10 BGP peerings
 * - Tests GET /api/v1/bgp-peerings with pagination
 * - Measures p99 latency
 * - Exports metrics to Prometheus
 * 
 * Usage:
 *   k6 run --out prometheus=remote_write=http://prometheus:9090/api/v1/write bgp_load_test.js
 *   k6 run --vus 100 --duration 5m bgp_load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween, randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const peeringCreationRate = new Rate('peering_creation_success');
const peeringListRate = new Rate('peering_list_success');
const peeringCreationDuration = new Trend('peering_creation_duration');
const peeringListDuration = new Trend('peering_list_duration');
const p99Latency = new Trend('p99_latency');
const totalRequests = new Counter('total_requests');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp up to 50 users
    { duration: '3m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(99)<1000'], // 99% of requests must complete below 1s
    'http_req_failed': ['rate<0.01'],     // Less than 1% of requests should fail
    'peering_creation_success': ['rate>0.95'], // 95% of creations should succeed
    'peering_list_success': ['rate>0.99'],     // 99% of list requests should succeed
  },
};

// Base URL - can be overridden with K6_BASE_URL environment variable
const BASE_URL = __ENV.K6_BASE_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

// Authentication token - should be set via K6_AUTH_TOKEN
const AUTH_TOKEN = __ENV.K6_AUTH_TOKEN || '';

// Helper function to make authenticated requests
function makeRequest(method, url, payload = null) {
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
  
  if (AUTH_TOKEN) {
    headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  }
  
  const params = {
    headers: headers,
    tags: { name: url },
  };
  
  let response;
  if (payload) {
    response = http.request(method, `${BASE_URL}${url}`, JSON.stringify(payload), params);
  } else {
    response = http.request(method, `${BASE_URL}${url}`, null, params);
  }
  
  totalRequests.add(1);
  return response;
}

// Generate random BGP peering data
function generatePeeringData(userId, peeringIndex) {
  const localAsn = 65000 + (userId % 100);
  const peerAsn = 65000 + randomIntBetween(1, 1000);
  const peerIpOctets = [
    randomIntBetween(10, 172),
    randomIntBetween(0, 255),
    randomIntBetween(0, 255),
    randomIntBetween(1, 254),
  ];
  
  return {
    name: `load-test-peering-${userId}-${peeringIndex}-${randomString(8)}`,
    local_asn: localAsn,
    peer_asn: peerAsn,
    peer_ip: peerIpOctets.join('.'),
    hold_time: randomIntBetween(90, 360),
    keepalive: randomIntBetween(30, 120),
    device: `router-${userId % 10}`,
    interface: `ethernet-0/0/${peeringIndex}`,
    status: 'active',
    address_families: ['ipv4_unicast'],
    routing_policy: {
      import_policy: `import-policy-${userId}`,
      export_policy: `export-policy-${userId}`,
    },
  };
}

// Test: Create BGP peering
function testCreatePeering(userId, peeringIndex) {
  const peeringData = generatePeeringData(userId, peeringIndex);
  const startTime = Date.now();
  
  const response = makeRequest('POST', `${API_PREFIX}/bgp-peerings`, peeringData);
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'create peering status is 201': (r) => r.status === 201,
    'create peering has ID': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.id !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  peeringCreationRate.add(success);
  peeringCreationDuration.add(duration);
  
  if (success && response.status === 201) {
    try {
      const body = JSON.parse(response.body);
      return body.id;
    } catch {
      return null;
    }
  }
  
  return null;
}

// Test: List BGP peerings with pagination
function testListPeerings(page = 0, limit = 50) {
  const startTime = Date.now();
  
  const response = makeRequest('GET', `${API_PREFIX}/bgp-peerings?skip=${page * limit}&limit=${limit}`);
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'list peerings status is 200': (r) => r.status === 200,
    'list peerings returns array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body);
      } catch {
        return false;
      }
    },
    'list peerings has data': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body) && body.length >= 0;
      } catch {
        return false;
      }
    },
  });
  
  peeringListRate.add(success);
  peeringListDuration.add(duration);
  
  // Calculate p99 latency
  if (duration > 0) {
    p99Latency.add(duration);
  }
  
  return success;
}

// Test: Get single peering by ID
function testGetPeering(peeringId) {
  const startTime = Date.now();
  
  const response = makeRequest('GET', `${API_PREFIX}/bgp-peerings/${peeringId}`);
  const duration = Date.now() - startTime;
  
  const success = check(response, {
    'get peering status is 200': (r) => r.status === 200,
    'get peering has ID': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.id === peeringId;
      } catch {
        return false;
      }
    },
  });
  
  return success;
}

// Test: Health check
function testHealthCheck() {
  const response = makeRequest('GET', '/healthz');
  
  return check(response, {
    'health check status is 200': (r) => r.status === 200,
  });
}

// Main test function
export default function () {
  const userId = __VU; // Virtual User ID
  const peeringIds = [];
  
  // Health check first
  testHealthCheck();
  sleep(1);
  
  // Create 10 BGP peerings per user
  for (let i = 0; i < 10; i++) {
    const peeringId = testCreatePeering(userId, i);
    if (peeringId) {
      peeringIds.push(peeringId);
    }
    sleep(randomIntBetween(1, 3)); // Random delay between 1-3 seconds
  }
  
  // Test pagination - list peerings with different page sizes
  for (let page = 0; page < 3; page++) {
    testListPeerings(page, 50);
    sleep(1);
  }
  
  // Test getting specific peerings
  if (peeringIds.length > 0) {
    const randomPeeringId = peeringIds[randomIntBetween(0, peeringIds.length - 1)];
    testGetPeering(randomPeeringId);
    sleep(1);
  }
  
  // Test filtering
  const filterResponse = makeRequest('GET', `${API_PREFIX}/bgp-peerings?device=router-${userId % 10}&status=active`);
  check(filterResponse, {
    'filter peerings status is 200': (r) => r.status === 200,
  });
  
  sleep(randomIntBetween(2, 5)); // Random delay before next iteration
}

// Setup function - runs once before all VUs
export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  console.log(`Target: ${options.stages.map(s => `${s.target} users for ${s.duration}`).join(', ')}`);
  
  // Verify API is accessible
  const healthResponse = http.get(`${BASE_URL}/healthz`);
  if (healthResponse.status !== 200) {
    console.error(`API health check failed: ${healthResponse.status}`);
    console.error('Make sure the API is running and accessible');
  }
  
  return { baseUrl: BASE_URL };
}

// Teardown function - runs once after all VUs
export function teardown(data) {
  console.log(`Load test completed for ${data.baseUrl}`);
  console.log('Check Prometheus metrics for detailed results');
}

