# Run the api on uvicorn
uvicorn api.main:app --port 5004 --workers 4 --limit-concurrency 100 --log-level debug --timeout-keep-alive 60