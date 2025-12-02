#!/usr/bin/env python3
"""
Run the Amazon Listing Optimizer application.
"""
import uvicorn

if __name__ == "__main__":
    print("Starting Amazon Listing Optimizer...")
    print("Open http://localhost:8000 in your browser")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
