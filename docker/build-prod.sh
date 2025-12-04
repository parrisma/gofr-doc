#!/bin/bash

docker build \
-f docker/Dockerfile.prod \
-t gofr-doc-prod:latest \
.