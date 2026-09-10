#!/bin/bash
set -euo pipefail

npm ci
npm run test
npm run build
docker build -t aegis:latest .
echo "deployment complete"
