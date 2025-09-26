#!/bin/bash

# Build all Tulip Ansible collections

set -e

COLLECTIONS=("edge" "player" "connectorhost")
BUILD_DIR="build"

# Create build directory
mkdir -p "$BUILD_DIR"

echo "Building all Tulip collections..."

for collection in "${COLLECTIONS[@]}"; do
    echo "Building tulip.$collection..."
    cd "collections/ansible_collections/tulip/$collection"
    
    # Build the collection (force overwrite if exists)
    ansible-galaxy collection build --output-path "../../../../$BUILD_DIR" --force
    
    # Return to root directory
    cd - > /dev/null
done

echo "All collections built successfully!"
echo "Built artifacts are in the $BUILD_DIR directory:"
ls -la "$BUILD_DIR"
