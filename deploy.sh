#!/bin/bash

echo "Stopping old bot process..."
pkill -f birthday.py || true

echo "Starting bot..."
nohup python3 birthday.py > bot.log 2>&1 &

echo "Deployment complete!"
