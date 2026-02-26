#!/bin/bash
exec uvicorn app.api.server:app --host 0.0.0.0 --port $PORT