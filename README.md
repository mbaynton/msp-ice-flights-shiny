# ICE Detainee Flights Analysis - MSP Airport

A Python Shiny application for visualizing ICE detainee flight data gathered by volunteer observers at MSP.

Currently hosted [here](https://019c6367-7c6c-2d03-83c2-c5959c6030ab.share.connect.posit.cloud/).

Various breakdowns and aggregations of the data are available via the "View" dropdown. Aggregations are over
the date range the user chooses.


## Data Source

The application loads data from an [Airtable database](https://airtable.com/appXo5spat4J3IQ9K/shrhjlIuy1V64gR4A/tbl4ZyyH4kmbsgDAw/viwrMDP3ciEuh3yXf) maintained by Nick Benson, containing:
- Flight dates and routes
- Detainee counts with counting methodology
- Airline information
- Destination details
- Offloading records

Data is fetched via the Airtable API using the `fetch_airtable_data.py` script and stored locally as `msp-ice-flights.csv`. The GitHub Actions workflow automatically updates this data every 2 hours.


## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. (Optional) For local data updates, set up Airtable access:
   - Obtain an Airtable Personal Access Token (PAT)
   - Add to `.envrc.local`: `export AIRTABLE_PAT='your-token-here'`
   - Run `python fetch_airtable_data.py` to download latest data
3. For GitHub Actions automation, add the `AIRTABLE_PAT` as a repository secret:
   - Go to repository Settings → Secrets and variables → Actions
   - Create a new secret named `AIRTABLE_PAT` with your Airtable token

## Usage

1. Run the application: `python run_app.py` (or `shiny run app.py`)
2. Open your browser to `http://localhost:8000`
3. Use the date range filter to focus on specific time periods
4. Toggle the events checkbox to show/hide key operational milestones
5. Hover over chart bars to see detailed information

## Automated Data Updates

The repository includes a GitHub Actions workflow (`.github/workflows/update-data.yml`) that:
- Runs every 2 hours automatically
- Fetches the latest data from Airtable
- Validates the app still runs correctly with the new data
- Commits and pushes updated data if changes are detected

This ensures the visualization always reflects the most current data without manual intervention.

## Interactive Tooltip Examples

When hovering over chart bars, you'll see detailed information like:

**Blue sections (Observed detainees):**
```
2025-11-05 (Wednesday)
Observed detainees: 20
Total detainees: 21
```

**Light blue sections (Estimated detainees):**
```
2025-11-05 (Wednesday)  
Estimated detainees: 1
Total detainees: 21
```

**Zero-value days (No flights):**
```
2025-11-06 (Thursday)
Observed detainees: 0
Total detainees: 0
```

## Event Markers

When the "Show key events" checkbox is enabled, red vertical lines will appear at significant dates with annotations explaining the events. These markers help contextualize changes in detention flight patterns against operational and personnel developments.


## Technical Implementation

- **Frontend**: Shiny for Python with Bootstrap styling via shinyswatch
- **Visualization**: Plotly for interactive charts with shinywidgets integration
- **Data Processing**: pandas for efficient data manipulation with gap filling
- **Data Source**: Airtable API via pyairtable library, exported to CSV
- **Automation**: GitHub Actions for scheduled data updates and validation
- **Event Timeline**: Custom Plotly annotations and vertical lines with smart date filtering
- **Timeline Continuity**: Automatic gap filling ensures complete daily timeline visualization
