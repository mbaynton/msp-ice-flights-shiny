import pandas as pd
from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_plotly
from datetime import date
import shinyswatch

from data import (
    load_data,
    aggregate_flights_per_day,
    aggregate_detainees_offloaded_per_day,
    aggregate_detainees_by_airline,
    aggregate_detainees_by_destination,
)
from charts import (
    create_bar_chart,
    create_timeseries_chart,
    create_horizontal_bar_chart,
)


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
