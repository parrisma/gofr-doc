#!/bin/bash

docker build \
-f docker/Dockerfile.prod \
-t doco_prod:latest \
.