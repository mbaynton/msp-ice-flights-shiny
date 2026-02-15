# ICE Detainee Flights Analysis - MSP Airport

A Python Shiny application for analyzing ICE detainee flight data from

## Features

- **Data Loading**: Automatically loads and processes ICE flight data from `msp-ice-flights.numbers` using the `numbers-parser` package
- **Complete Timeline**: Fills in missing days with zero values to provide a continuous daily timeline
- **Interactive Date Filtering**: Filter data by custom date ranges with intuitive date picker controls
- **Key Events Timeline**: Toggle-able vertical markers highlighting significant events and operational milestones
- **Interactive Visualizations**: Displays daily detainee totals with interactive stacked bar charts featuring hover tooltips
- **Rich Tooltips**: Hover over any bar to see detailed information including date, day of week, specific counts, and totals
- **Responsive Dashboard**: Bootstrap-styled interface with real-time summary statistics that update based on filters
- **Data Accuracy**: Clearly distinguishes between observed detainee counts (confirmed sightings) and estimated counts

## Data Source

The application processes data from the "ICE at MSP" sheet in the provided Numbers spreadsheet, containing:
- Flight dates and routes
- Detainee counts (total and observed)
- Airline information  
- Destination details

## Key Insights

From the complete dataset:
- **1,182 total days** in the analysis period (November 2025 - January 2029)
- **62 days with ICE detainee flights** (5.2% of all days)
- **1,120 days without flights** (94.8% of all days)
- **3,612 total detainees** across all flight days  
- **1,389 observed detainees** (38.4% directly confirmed)
- **58.3 average detainees per flight day**
- **3.1 average detainees across all days** (including zero days)

## Interactive Features

### Complete Daily Timeline
- **Gap Filling**: Automatically fills missing days between first and last flight dates with zero values
- **Continuous Visualization**: Shows all days in the date range, making patterns and gaps in operations clearly visible
- **Context Preservation**: Maintains temporal context by showing periods of operational activity vs. inactivity

### Date Range Filtering
- **Custom Ranges**: Select any start and end date within the dataset bounds
- **Real-time Updates**: Charts and statistics automatically update when filter changes
- **Reset Function**: Quick button to return to full dataset view
- **Bounded Inputs**: Date pickers are automatically limited to available data range

### Key Events Timeline
- **Toggle Control**: Checkbox to show/hide key events (enabled by default)
- **Visual Markers**: Red dashed vertical lines mark significant dates
- **Event Annotations**: Hover-able text labels explaining each event
- **Smart Filtering**: Only shows events within the selected date range

#### Tracked Events
- **December 4, 2025**: Operation Metro Surge Begins
- **January 7, 2026**: Killing of Renée Good
- **January 24, 2026**: Killing of Alex Pretti
- **January 26, 2026**: Bovino replaced by Homan
- **February 4, 2026**: 700 agent drawdown
- **February 12, 2026**: Homan: operation ending

### Interactive Charts (Plotly-powered)
- **Hover Tooltips**: Rich tooltips showing date, day of week, count details, and daily totals
- **Zero-Day Visualization**: Days without flights appear as zero-height bars, maintaining timeline continuity
- **Zoom & Pan**: Standard plotly controls for detailed examination
- **Stacked Bars**: Clear visual distinction between observed and estimated counts
- **Professional Styling**: Clean, modern appearance with consistent color scheme
- **Export Options**: Built-in download options for charts (PNG, SVG, PDF)

### Dynamic Statistics
All summary cards update based on current filter:
- Days with flights in selected period
- Total detainees in selected period  
- Observed detainees in selected period
- Average detainees per day in selected period

## Requirements

- Python 3.12+
- numbers-parser
- pandas
- shiny
- plotly
- shinyswatch
- shinywidgets

## Usage

1. Ensure `msp-ice-flights.numbers` is in the project root directory
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python run_app.py`
4. Open your browser to `http://localhost:8000`
5. Use the date range filter to focus on specific time periods
6. Toggle the events checkbox to show/hide key operational milestones
7. Hover over chart bars to see detailed information

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

## Data Processing Notes

- Excludes header rows and summary rows from analysis
- Calculates estimated detainees as: `Total - Observed`
- **Gap Filling**: Automatically adds zero-value entries for all missing days between first and last flight dates
- Aggregates daily totals across all flights per day
- Handles missing data appropriately
- Uses original column names internally but displays user-friendly terminology

## Technical Implementation

- **Frontend**: Shiny for Python with Bootstrap styling via shinyswatch
- **Visualization**: Plotly for interactive charts with shinywidgets integration
- **Data Processing**: pandas for efficient data manipulation with gap filling
- **File Parsing**: numbers-parser for reading Apple Numbers spreadsheets
- **Event Timeline**: Custom Plotly annotations and vertical lines with smart date filtering
- **Timeline Continuity**: Automatic gap filling ensures complete daily timeline visualization

## Example Use Cases

- **Monthly Analysis**: Filter to specific months to see seasonal patterns including operational downtime
- **Peak Period Focus**: Isolate high-activity periods for detailed analysis
- **Operational Gaps**: Identify periods without flight activity using the continuous timeline
- **Event Impact Analysis**: Compare detention flight patterns before/after key events
- **Trend Analysis**: Use event markers and continuous timeline to understand operational changes over time
- **Data Validation**: Check specific dates against external sources using hover tooltips
- **Daily Breakdowns**: Examine individual days by hovering over specific bars (including zero days)
- **Export Analysis**: Download charts for reports or presentations

## Future Enhancements

The application is structured to easily support additional features such as:
- Route analysis using "Day's Route" column data
- Filtering by destinations or airlines
- Enhanced visualizations (maps, trend lines)
- Data export capabilities for raw data
- Comparative analysis tools
- Time series forecasting
- Additional event categories and customization
- Weekly/monthly aggregation views