#!/usr/bin/env python3
"""
Run the ICE Flights Shiny Application

This script starts the Shiny web application for analyzing ICE deportation flights from MSP airport.
"""

if __name__ == "__main__":
    from app import app
    
    print("Starting ICE Flights Analysis Application...")
    print("The application will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the application.")
    
    # Run the app
    app.run(host="0.0.0.0", port=8000)