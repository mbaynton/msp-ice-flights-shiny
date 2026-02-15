import numbers_parser
import pandas as pd
from shiny import App, render, ui, reactive
import plotly.graph_objects as go
from shinywidgets import output_widget, render_plotly
from datetime import datetime, date
import shinyswatch


def load_data():
    """Load and process the ICE flights data from the Numbers spreadsheet."""
    
    # Load the Numbers file
    doc = numbers_parser.Document("msp-ice-flights.numbers")
    
    # Get the data from the first table in the first sheet
    table = doc.sheets[0].tables[0]
    data = table.rows(values_only=True)
    
    # Convert to pandas DataFrame
    df_raw = pd.DataFrame(data)
    
    # The column headers are in row 1 (index 1)
    header_row = df_raw.iloc[1].tolist()
    
    # Create cleaned dataframe with proper headers
    # Skip the first row (title) and use row 1 as headers, skip last 2 rows (empty and sum)
    df_clean = df_raw.iloc[2:-2].copy()
    df_clean.columns = header_row
    
    # Clean up the data types and focus on relevant columns
    df_clean['Date'] = pd.to_datetime(df_clean['Date'])
    df_clean['Deportees'] = pd.to_numeric(df_clean['Deportees'], errors='raise')
    df_clean['Deportee (observed)'] = pd.to_numeric(df_clean['Deportee (observed)'], errors='raise').fillna(0)
    
    # Calculate estimated detainees (total - observed)
    df_clean['Deportees_Estimated'] = df_clean['Deportees'] - df_clean['Deportee (observed)']
    
    # Filter to rows with non-null Deportees data
    non_null_detainees = df_clean[df_clean['Deportees'].notna()]
    
    # Create daily summary
    daily_summary = non_null_detainees.groupby(non_null_detainees['Date'].dt.date).agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum'
    }).reset_index()
    
    # Ensure proper datetime format
    daily_summary['Date'] = pd.to_datetime(daily_summary['Date'])
    
    # Fill in missing days with zero values
    if not daily_summary.empty:
        # Create a complete date range from min to max date
        min_date = daily_summary['Date'].min()
        max_date = daily_summary['Date'].max()
        complete_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        # Create a complete dataframe with all dates
        complete_df = pd.DataFrame({'Date': complete_date_range})
        
        # Merge with existing data, filling missing days with zeros
        daily_summary = complete_df.merge(daily_summary, on='Date', how='left').fillna({
            'Deportees': 0,
            'Deportee (observed)': 0,
            'Deportees_Estimated': 0
        })
    
    return daily_summary, df_clean


def create_bar_chart(daily_data, show_events=True):
    """Create an interactive stacked bar chart showing observed vs estimated detainees by day."""
    
    # Define key events
    key_events = [
        {"date": "2025-12-04", "label": "Operation Metro Surge Begins"},
        {"date": "2026-01-07", "label": "Killing of Renée Good"},
        {"date": "2026-01-24", "label": "Killing of Alex Pretti"},
        {"date": "2026-01-26", "label": "Bovino replaced by Homan"},
        {"date": "2026-02-04", "label": "700 agent drawdown"},
        {"date": "2026-02-12", "label": "Homan: operation ending"}
    ]
    
    # Prepare data for plotting
    plot_data = daily_data.copy()
    plot_data['FormattedDate'] = plot_data['Date'].dt.strftime('%Y-%m-%d')
    plot_data['DayOfWeek'] = plot_data['Date'].dt.strftime('%A')
    
    # Create the interactive plotly chart
    fig = go.Figure()
    
    # Add observed detainees bar
    fig.add_trace(go.Bar(
        x=plot_data['FormattedDate'],
        y=plot_data['Deportee (observed)'],
        name='Observed',
        marker_color='#2E86AB',
        hovertemplate='<b>%{x} (%{customdata[0]})</b><br>' +
                      'Observed detainees: <b>%{y}</b><br>' +
                      'Total detainees: <b>%{customdata[1]}</b>' +
                      '<extra></extra>',
        customdata=list(zip(plot_data['DayOfWeek'], plot_data['Deportees']))
    ))
    
    # Add event markers if requested
    if show_events and not plot_data.empty:
        max_y = plot_data['Deportees'].max()
        
        for event in key_events:
            event_date = event["date"]
            event_label = event["label"]
            
            # Check if event date is within the data range
            if event_date >= plot_data['FormattedDate'].min() and event_date <= plot_data['FormattedDate'].max():
                # Add vertical line
                fig.add_vline(
                    x=event_date,
                    line_dash="dash",
                    line_color="red",
                    line_width=2,
                    opacity=0.7
                )
                
                # Add annotation
                fig.add_annotation(
                    x=event_date,
                    y=max_y * 1.1,  # Position above the highest bar
                    text=event_label,
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="red",
                    ax=0,
                    ay=-40,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="red",
                    borderwidth=1,
                    font=dict(size=10, color="red"),
                    textangle=-35
                )
    
    # Add estimated detainees bar  
    fig.add_trace(go.Bar(
        x=plot_data['FormattedDate'],
        y=plot_data['Deportees_Estimated'],
        name='Estimated',
        marker_color='#73b2cc',
        hovertemplate='<b>%{x} (%{customdata[0]})</b><br>' +
                      'Estimated detainees: <b>%{y}</b><br>' +
                      'Total detainees: <b>%{customdata[1]}</b>' +
                      '<extra></extra>',
        customdata=list(zip(plot_data['DayOfWeek'], plot_data['Deportees']))
    ))
    
    # Update layout for stacked bars and styling
    fig.update_layout(
        title={
            'text': 'ICE Detainee Flights from MSP Airport<br><sub>Daily totals showing observed vs estimated detainee counts (hover for details)</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        xaxis={
            'title': 'Date',
            'tickangle': 45,
            'type': 'category'
        },
        yaxis={
            'title': 'Number of Detainees'
        },
        barmode='stack',
        hovermode='x unified',
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        },
        margin=dict(b=100, t=150),  # Extra top margin for annotations
        plot_bgcolor='white',
        paper_bgcolor='white',
        # Enable responsive resizing for width only
        autosize=True,
    )
    
    # Style the axes
    fig.update_xaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)
    
    return fig


# Load data at startup
daily_data, flight_data = load_data()

# Get date range for filters
min_date = daily_data['Date'].min().date()
max_date = daily_data['Date'].max().date()

# Set default end date to current server date, but cap at max_date if current date is beyond data range
current_date = date.today()
default_end_date = min(current_date, max_date)

# Define UI
app_ui = ui.page_fluid(    
    ui.div(
        {"class": "container-fluid"},
        ui.h1("ICE Detainee Flight Departures from MSP Airport", class_="text-center mb-4"),
        ui.p(
            f"This application visualizes ICE detainee flight data departing MSP Airport "
            f"({min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}).",
            class_="text-center text-muted mb-4"
        ),
        
        # Date range filter
        ui.div(
            {"class": "row mb-4"},
            ui.div(
                {"class": "col-12"},
                ui.div(
                    {"class": "card"},
                    ui.div(
                        {"class": "card-body"},
                        ui.h5("Filter by Date Range", class_="card-title"),
                        ui.div(
                            {"class": "row"},
                            ui.div(
                                {"class": "col-md-6"},
                                ui.input_date(
                                    "start_date",
                                    "Start Date:",
                                    value=min_date,
                                    min=min_date,
                                    max=max_date
                                )
                            ),
                            ui.div(
                                {"class": "col-md-6"},
                                ui.input_date(
                                    "end_date", 
                                    "End Date:",
                                    value=default_end_date,
                                    min=min_date,
                                    max=max_date
                                )
                            )
                        ),
                        ui.div(
                            {"class": "row mt-3"},
                            ui.div(
                                {"class": "col-12"},
                                ui.input_checkbox(
                                    "show_events",
                                    "Show key events as vertical lines",
                                    value=True
                                ),
                                ui.p("Key events include Operation Metro Surge, personnel changes, and operational milestones.", 
                                     class_="text-muted small mt-1")
                            )
                        ),
                        ui.div(
                            {"class": "mt-2"},
                            ui.input_action_button("reset_dates", "Reset to Full Range", class_="btn btn-outline-secondary btn-sm")
                        )
                    )
                )
            )
        ),
        
        # Main chart
        ui.div(
            ui.div(
                ui.h3("Daily Detainee Totals"),
                ui.p(
                    "This chart shows the total number of detainees on all ICE flights departing MSP each day. "
                    "Bars are split into observed counts (boarding an aircraft) and estimated counts "
                    "using means such as capacity of ground vehicles observed.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3"),
                output_widget("daily_chart")
            )
        ),
        
        # Summary statistics
        ui.div(
            {"class": "row mt-4"},
            ui.div(
                {"class": "col-md-3"},
                ui.div(
                    {"class": "card text-center"},
                    ui.div(
                        {"class": "card-body"},
                        ui.output_text("days_count", inline=True),
                        ui.p("Days with flights", class_="card-text text-muted")
                    )
                )
            ),
            ui.div(
                {"class": "col-md-3"}, 
                ui.div(
                    {"class": "card text-center"},
                    ui.div(
                        {"class": "card-body"},
                        ui.output_text("total_detainees", inline=True),
                        ui.p("Total detainees", class_="card-text text-muted")
                    )
                )
            ),
            ui.div(
                {"class": "col-md-3"},
                ui.div(
                    {"class": "card text-center"},
                    ui.div(
                        {"class": "card-body"},
                        ui.output_text("observed_detainees", inline=True),
                        ui.p("Observed detainees", class_="card-text text-muted")
                    )
                )
            ),
            ui.div(
                {"class": "col-md-3"},
                ui.div(
                    {"class": "card text-center"},
                    ui.div(
                        {"class": "card-body"},
                        ui.output_text("average_per_day", inline=True),
                        ui.p("Average per day", class_="card-text text-muted")
                    )
                )
            )
        ),
    ),
    theme=shinyswatch.theme.flatly
)

# Define server logic
def server(input, output, session):
    
    @reactive.Calc
    def filtered_data():
        """Filter data based on selected date range."""
        start = pd.to_datetime(input.start_date())
        end = pd.to_datetime(input.end_date())
        
        # Filter the daily data
        filtered = daily_data[
            (daily_data['Date'] >= start) & 
            (daily_data['Date'] <= end)
        ]
        
        return filtered
    
    @output
    @render_plotly
    def daily_chart():
        return create_bar_chart(filtered_data(), show_events=input.show_events())
    
    @output
    @render.text
    def days_count():
        return f"{len(filtered_data())}"
    
    @output 
    @render.text
    def total_detainees():
        return f"{filtered_data()['Deportees'].sum():.0f}"
    
    @output
    @render.text 
    def observed_detainees():
        return f"{filtered_data()['Deportee (observed)'].sum():.0f}"
    
    @output
    @render.text
    def average_per_day():
        data = filtered_data()
        if len(data) > 0:
            return f"{data['Deportees'].mean():.1f}"
        else:
            return "0.0"
    
    @reactive.Effect
    @reactive.event(input.reset_dates)
    def reset_date_range():
        """Reset date inputs to full range."""
        ui.update_date("start_date", value=min_date)
        ui.update_date("end_date", value=max_date)

# Create the app
app = App(app_ui, server)