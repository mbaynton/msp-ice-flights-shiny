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


def aggregate_flights_per_day(flight_df):
    """Count number of flights per day."""
    flights_by_day = flight_df.groupby(
        pd.to_datetime(flight_df['Date']).dt.date
    ).size().reset_index(name='Flight_Count')

    flights_by_day['Date'] = pd.to_datetime(flights_by_day['Date'])

    # Fill missing days with zeros (match existing pattern from load_data)
    if not flights_by_day.empty:
        min_date = flights_by_day['Date'].min()
        max_date = flights_by_day['Date'].max()
        complete_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        complete_df = pd.DataFrame({'Date': complete_date_range})

        flights_by_day = complete_df.merge(flights_by_day, on='Date', how='left').fillna({
            'Flight_Count': 0
        })

    return flights_by_day


def aggregate_detainees_offloaded_per_day(flight_df):
    """Sum detainees offloaded per day (all treated as observed)."""
    flight_df_copy = flight_df.copy()

    # Convert Deportees Off to numeric, handle nulls
    flight_df_copy['Deportees Off'] = pd.to_numeric(
        flight_df_copy['Deportees Off'],
        errors='coerce'
    ).fillna(0)

    offloaded_by_day = flight_df_copy.groupby(
        pd.to_datetime(flight_df_copy['Date']).dt.date
    )['Deportees Off'].sum().reset_index()

    offloaded_by_day['Date'] = pd.to_datetime(offloaded_by_day['Date'])

    # Fill missing days with zeros
    if not offloaded_by_day.empty:
        min_date = offloaded_by_day['Date'].min()
        max_date = offloaded_by_day['Date'].max()
        complete_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        complete_df = pd.DataFrame({'Date': complete_date_range})

        offloaded_by_day = complete_df.merge(offloaded_by_day, on='Date', how='left').fillna({
            'Deportees Off': 0
        })

    return offloaded_by_day


def aggregate_detainees_by_airline(flight_df):
    """Aggregate detainees by airline, split by observed vs estimated."""
    # Exclude null airlines
    valid_airlines = flight_df[flight_df['Airline'].notna()].copy()

    # Normalize airline names: trim spaces, title case
    valid_airlines['Airline'] = valid_airlines['Airline'].str.strip().str.title()

    airline_totals = valid_airlines.groupby('Airline').agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum'
    }).reset_index()

    # Sort ascending for horizontal bars (bottom-to-top reading)
    airline_totals = airline_totals.sort_values('Deportees', ascending=True)

    return airline_totals


def aggregate_detainees_by_destination(flight_df):
    """Aggregate detainees by destination airport, split by observed vs estimated."""
    # Exclude null destinations
    valid_destinations = flight_df[flight_df['To'].notna()].copy()

    destination_totals = valid_destinations.groupby('To').agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum'
    }).reset_index()

    # Sort ascending for horizontal bars (bottom-to-top reading)
    destination_totals = destination_totals.sort_values('Deportees', ascending=True)

    return destination_totals


def create_bar_chart(daily_data, show_events=True):
    """Create an interactive stacked bar chart showing observed vs estimated detainees by day."""
    
    # Define key events
    key_events = [
        {"date": "2025-12-04", "label": "Operation Metro Surge begins"},
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


def create_timeseries_chart(data, value_col=None, title='', yaxis_title='', show_events=True,
                            color='#2E86AB', stacked=False, observed_col=None, estimated_col=None):
    """Create a time-series bar chart for daily aggregated data.

    Args:
        data: DataFrame with Date column and value columns
        value_col: Single value column (for simple bar charts)
        stacked: If True, use observed_col and estimated_col for stacked bars
        observed_col: Column name for observed values (when stacked=True)
        estimated_col: Column name for estimated values (when stacked=True)
    """

    # Key events (same as existing)
    key_events = [
        {"date": "2025-12-04", "label": "Operation Metro Surge begins"},
        {"date": "2026-01-07", "label": "Killing of Renée Good"},
        {"date": "2026-01-24", "label": "Killing of Alex Pretti"},
        {"date": "2026-01-26", "label": "Bovino replaced by Homan"},
        {"date": "2026-02-04", "label": "700 agent drawdown"},
        {"date": "2026-02-12", "label": "Homan: operation ending"}
    ]

    # Prepare data
    plot_data = data.copy()
    plot_data['FormattedDate'] = plot_data['Date'].dt.strftime('%Y-%m-%d')
    plot_data['DayOfWeek'] = plot_data['Date'].dt.strftime('%A')

    # Create figure
    fig = go.Figure()

    if stacked and observed_col and estimated_col:
        # Add observed bar
        fig.add_trace(go.Bar(
            x=plot_data['FormattedDate'],
            y=plot_data[observed_col],
            name='Observed',
            marker_color='#2E86AB',
            hovertemplate='<b>%{x} (%{customdata[0]})</b><br>' +
                          'Observed: <b>%{y}</b><br>' +
                          'Total: <b>%{customdata[1]}</b>' +
                          '<extra></extra>',
            customdata=list(zip(plot_data['DayOfWeek'], plot_data[observed_col] + plot_data[estimated_col]))
        ))

        # Add estimated bar
        fig.add_trace(go.Bar(
            x=plot_data['FormattedDate'],
            y=plot_data[estimated_col],
            name='Estimated',
            marker_color='#73b2cc',
            hovertemplate='<b>%{x} (%{customdata[0]})</b><br>' +
                          'Estimated: <b>%{y}</b><br>' +
                          'Total: <b>%{customdata[1]}</b>' +
                          '<extra></extra>',
            customdata=list(zip(plot_data['DayOfWeek'], plot_data[observed_col] + plot_data[estimated_col]))
        ))

        max_y = (plot_data[observed_col] + plot_data[estimated_col]).max()
    else:
        # Simple bar chart
        fig.add_trace(go.Bar(
            x=plot_data['FormattedDate'],
            y=plot_data[value_col],
            name=yaxis_title,
            marker_color=color,
            hovertemplate='<b>%{x} (%{customdata})</b><br>' +
                          f'{yaxis_title}: <b>%{{y}}</b>' +
                          '<extra></extra>',
            customdata=plot_data['DayOfWeek']
        ))

        max_y = plot_data[value_col].max()

    # Add event markers if requested
    if show_events and not plot_data.empty and max_y > 0:
        for event in key_events:
            event_date = event["date"]
            event_label = event["label"]

            if event_date >= plot_data['FormattedDate'].min() and event_date <= plot_data['FormattedDate'].max():
                fig.add_vline(
                    x=event_date,
                    line_dash="dash",
                    line_color="red",
                    line_width=2,
                    opacity=0.7
                )

                fig.add_annotation(
                    x=event_date,
                    y=max_y * 1.1,
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

    # Update layout (match existing style)
    fig.update_layout(
        title={
            'text': title,
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
            'title': yaxis_title
        },
        barmode='stack' if stacked else 'group',
        hovermode='x unified',
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        } if stacked else {},
        margin=dict(b=100, t=150),
        plot_bgcolor='white',
        paper_bgcolor='white',
        autosize=True,
    )

    fig.update_xaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)
    fig.update_yaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)

    return fig


def create_horizontal_bar_chart(data, category_col, value_col=None, title='', xaxis_title='',
                                 color='#2E86AB', stacked=False, observed_col=None, estimated_col=None):
    """Create a horizontal bar chart for categorical aggregations.

    Args:
        data: DataFrame with category column and value columns
        category_col: Column name for categories (Y-axis)
        value_col: Single value column (for simple bar charts)
        stacked: If True, use observed_col and estimated_col for stacked bars
        observed_col: Column name for observed values (when stacked=True)
        estimated_col: Column name for estimated values (when stacked=True)
    """

    fig = go.Figure()

    if stacked and observed_col and estimated_col:
        # Add observed bar
        fig.add_trace(go.Bar(
            x=data[observed_col],
            y=data[category_col],
            orientation='h',
            name='Observed',
            marker_color='#2E86AB',
            hovertemplate='<b>%{y}</b><br>' +
                          'Observed: <b>%{x}</b><br>' +
                          'Total: <b>%{customdata}</b>' +
                          '<extra></extra>',
            customdata=data[observed_col] + data[estimated_col]
        ))

        # Add estimated bar
        fig.add_trace(go.Bar(
            x=data[estimated_col],
            y=data[category_col],
            orientation='h',
            name='Estimated',
            marker_color='#73b2cc',
            hovertemplate='<b>%{y}</b><br>' +
                          'Estimated: <b>%{x}</b><br>' +
                          'Total: <b>%{customdata}</b>' +
                          '<extra></extra>',
            customdata=data[observed_col] + data[estimated_col]
        ))
    else:
        # Simple horizontal bar chart
        fig.add_trace(go.Bar(
            x=data[value_col],
            y=data[category_col],
            orientation='h',
            marker_color=color,
            hovertemplate='<b>%{y}</b><br>' +
                          f'{xaxis_title}: <b>%{{x}}</b>' +
                          '<extra></extra>'
        ))

    # Update layout
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        xaxis={
            'title': xaxis_title
        },
        yaxis={
            'title': ''
        },
        barmode='stack' if stacked else 'group',
        hovermode='y unified',
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'right',
            'x': 1
        } if stacked else {},
        margin=dict(l=150, b=100, t=150),  # Extra left margin for labels
        plot_bgcolor='white',
        paper_bgcolor='white',
        autosize=True,
    )

    fig.update_xaxes(showgrid=True, gridcolor='lightgray', gridwidth=1)
    fig.update_yaxes(showgrid=False)

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
app_ui = ui.page_sidebar(
    # Sidebar with filter controls
    ui.sidebar(
        ui.input_select(
            "view_type",
            "View:",
            choices={
                "daily_detainees": "Daily Detainees",
                "flights_per_day": "Flights per Day",
                "detainees_offloaded": "Detainees Offloaded per Day",
                "detainees_by_airline": "Detainees by Airline",
                "detainees_by_destination": "Detainees by Destination"
            },
            selected="daily_detainees"
        ),
        ui.input_date(
            "start_date",
            "Start Date:",
            value=min_date,
            min=min_date,
            max=max_date
        ),
        ui.input_date(
            "end_date",
            "End Date:",
            value=default_end_date,
            min=min_date,
            max=max_date
        ),
        ui.output_ui("events_control"),
        ui.input_action_button("reset_dates", "Reset to Full Range", class_="btn btn-outline-secondary btn-sm"),
        ui.p("Data compiled by Nick Benson, ", ui.a("MN50501", href="https://mn50501.org", target="_blank")),
        id="sidebar",
    ),

        # CSS to make the Plotly chart fill its card and respond to width changes
    ui.tags.style("""
        #daily_chart {
            height: 65vh !important;
            min-height: 450px;
        }
        #daily_chart .plotly.plot-container,
        #daily_chart .js-plotly-plot,
        #daily_chart .plot-container,
        #daily_chart .svg-container {
            height: 100% !important;
            width: 100% !important;
        }
    """),

    # Page title
    ui.h1("ICE Detainee Flight Departures from MSP Airport", class_="text-center mb-4"),
    ui.p(
        f"This application visualizes ICE detainee flight data departing MSP Airport "
        f"({min_date.strftime('%B %Y')} - {max_date.strftime('%B %Y')}).",
        class_="text-center text-muted mb-4"
    ),

    # Main chart card
    ui.card(
        ui.card_header(ui.output_text("card_header", inline=True)),
        ui.card_body(
            ui.output_ui("chart_description"),
            output_widget("daily_chart")
        ),
        full_screen=True,
    ),

    # Summary statistics
    ui.layout_columns(
        ui.card(
            ui.card_body(
                ui.output_text("days_count", inline=True),
                ui.p("Days with flights", class_="card-text text-muted"),
                class_="text-center"
            )
        ),
        ui.card(
            ui.card_body(
                ui.output_text("total_detainees", inline=True),
                ui.p("Total detainees", class_="card-text text-muted"),
                class_="text-center"
            )
        ),
        ui.card(
            ui.card_body(
                ui.output_text("observed_detainees", inline=True),
                ui.p("Observed detainees", class_="card-text text-muted"),
                class_="text-center"
            )
        ),
        ui.card(
            ui.card_body(
                ui.output_text("average_per_day", inline=True),
                ui.p("Average per day", class_="card-text text-muted"),
                class_="text-center"
            )
        ),
        col_widths=(3, 3, 3, 3)
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

    @reactive.Calc
    def filtered_flight_data():
        """Filter flight-level data based on selected date range."""
        start = pd.to_datetime(input.start_date())
        end = pd.to_datetime(input.end_date())

        # Filter the flight_data (df_clean)
        filtered = flight_data[
            (pd.to_datetime(flight_data['Date']) >= start) &
            (pd.to_datetime(flight_data['Date']) <= end)
        ]

        return filtered

    @render.ui
    def events_control():
        """Conditionally show events checkbox only for time-series views."""
        view = input.view_type()

        if view in ["daily_detainees", "flights_per_day", "detainees_offloaded"]:
            return ui.TagList(
                ui.input_checkbox(
                    "show_events",
                    "Show key events as vertical lines",
                    value=True
                ),
                ui.p("Key events include Operation Metro Surge, personnel changes, and operational milestones.",
                     class_="text-muted small")
            )
        else:
            return ui.TagList()

    @render.text
    def card_header():
        """Dynamic card header based on view."""
        view = input.view_type()

        headers = {
            "daily_detainees": "Daily Detainees Flown",
            "flights_per_day": "Flights per Day",
            "detainees_offloaded": "Detainees Offloaded per Day",
            "detainees_by_airline": "Detainees by Airline",
            "detainees_by_destination": "Detainees by Destination"
        }

        return headers.get(view, "Data View")

    @render.ui
    def chart_description():
        """Dynamic chart description based on view."""
        view = input.view_type()

        descriptions = {
            "daily_detainees": ui.TagList(
                ui.p(
                    "This chart shows the total number of detainees on all ICE flights departing MSP each day. "
                    "Bars are split into count observed boarding an aircraft and estimated counts "
                    "using means such as capacity of ground vehicles in airport convoys.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3")
            ),
            "flights_per_day": ui.TagList(
                ui.p(
                    "This chart shows the number of individual ICE flights departing MSP each day.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3")
            ),
            "detainees_offloaded": ui.TagList(
                ui.p(
                    "This chart shows the number of detainees offloaded from flights each day. "
                    "All offloaded detainees are treated as observed (no estimates). "
                    "Note: Offloading data is sparse, with most days having no recorded offloadings.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3")
            ),
            "detainees_by_airline": ui.TagList(
                ui.p(
                    "This chart shows the total number of detainees transported by each airline carrier "
                    "across all flights in the selected date range. "
                    "Bars are split into observed and estimated counts.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3")
            ),
            "detainees_by_destination": ui.TagList(
                ui.p(
                    "This chart shows the total number of detainees sent to each destination airport "
                    "across all flights in the selected date range. "
                    "Bars are split into observed and estimated counts.",
                    class_="text-muted mb-3"
                ),
                ui.p("Hover over bars for detailed information.", class_="text-muted mb-3")
            )
        }

        return descriptions.get(view, ui.p("", class_="text-muted mb-3"))

    @render_plotly
    def daily_chart():
        """Render chart based on selected view type."""
        view = input.view_type()

        # Get show_events value safely
        try:
            show_events = input.show_events()
        except (AttributeError, KeyError):
            show_events = False

        if view == "daily_detainees":
            # Original view
            return create_bar_chart(filtered_data(), show_events=show_events)

        elif view == "flights_per_day":
            agg_data = aggregate_flights_per_day(filtered_flight_data())
            return create_timeseries_chart(
                agg_data,
                value_col='Flight_Count',
                title='ICE Flights per Day from MSP Airport<br><sub>Number of individual flights each day (hover for details)</sub>',
                yaxis_title='Number of Flights',
                show_events=show_events,
                color='#2E86AB'
            )

        elif view == "detainees_offloaded":
            agg_data = aggregate_detainees_offloaded_per_day(filtered_flight_data())
            return create_timeseries_chart(
                agg_data,
                value_col='Deportees Off',
                title='Detainees Offloaded per Day from MSP Airport<br><sub>Number of detainees offloaded from flights each day (all observed, hover for details)</sub>',
                yaxis_title='Detainees Offloaded',
                show_events=show_events,
                color='#E63946'
            )

        elif view == "detainees_by_airline":
            agg_data = aggregate_detainees_by_airline(filtered_flight_data())
            return create_horizontal_bar_chart(
                agg_data,
                category_col='Airline',
                title='Total Detainees by Airline<br><sub>Observed vs estimated detainee counts by airline carrier (hover for details)</sub>',
                xaxis_title='Total Detainees',
                stacked=True,
                observed_col='Deportee (observed)',
                estimated_col='Deportees_Estimated'
            )

        elif view == "detainees_by_destination":
            agg_data = aggregate_detainees_by_destination(filtered_flight_data())
            return create_horizontal_bar_chart(
                agg_data,
                category_col='To',
                title='Total Detainees by Destination<br><sub>Observed vs estimated detainee counts by destination airport (hover for details)</sub>',
                xaxis_title='Total Detainees',
                stacked=True,
                observed_col='Deportee (observed)',
                estimated_col='Deportees_Estimated'
            )
        else:
            # Default to daily detainees view
            return create_bar_chart(filtered_data(), show_events=show_events)

    @render.text
    def days_count():
        return f"{len(filtered_data())}"
    
    @render.text
    def total_detainees():
        return f"{filtered_data()['Deportees'].sum():.0f}"
    
    @render.text 
    def observed_detainees():
        return f"{filtered_data()['Deportee (observed)'].sum():.0f}"
    
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
