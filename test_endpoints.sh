#!/bin/bash

echo "--- Running Integration Tests ---"

echo "\n[1] Testing Personalized Feed..."
curl "http://168.107.18.155:3000/me/feed?limit=10"

echo "\n\n[2] Testing Company Context Rebuild..."
curl -X POST "http://168.107.18.155:3000/admin/context/rebuild?company=NVIDIA"
echo "\nFetching context:"
curl "http://168.107.18.155:3000/company/context?company=NVIDIA"

echo "\n\n[3] Testing Market Risk Refresh..."
curl -X POST "http://168.107.18.155:3000/admin/market/risk/refresh?ticker=NVDA"
echo "\nFetching risk data:"
curl "http://168.107.18.155:3000/market/risk?ticker=NVDA"

echo "\n\n[4] Testing GEX Curve..."
curl "http://168.107.18.155:3000/market/gex_curve?ticker=NVDA"

echo "\n\n[5] Testing Alert Settings..."
curl -X POST "http://168.107.18.155:3000/me/settings/alerts" \
 -H "Content-Type: application/json" \
 -d '{"quiet_hours":{"start":"23:00","end":"07:00"},"min_importance":70,"categories":["regulation","financials"],"severity_min":"LOW","gex":{"enabled":true,"zero_band_pct":1.0},"maxpain":{"enabled":true,"gap_pct":3.0}}'

echo "\n\nTo test SSE stream, run this in another terminal:"
echo 'curl -N "http://168.107.18.155:3000/me/alerts/stream"'

echo "\n\n--- Integration Tests Finished ---"
