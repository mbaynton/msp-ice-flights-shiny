import numbers_parser
import pandas as pd


EST_METHOD_DESCRIPTIONS = {
    'V': 'Formula based on the number and types of vehicles bringing detainees to the flight',
    'A': 'Average based on similar flights in same timeframe',
    'O': 'Estimate based on an observer who was present, but not directly counting',
}


def _format_est_methods(methods_series):
    """Aggregate estimation method codes into a combined descriptive string."""
    unique_codes = methods_series.dropna().unique()
    descriptions = []
    for code in sorted(str(c).strip() for c in unique_codes):
        if code in EST_METHOD_DESCRIPTIONS:
            descriptions.append(EST_METHOD_DESCRIPTIONS[code])
    if not descriptions:
        return ''
    return '; '.join(descriptions)


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

    # Rename the estimation method column for convenience
    df_clean = df_clean.rename(columns={
        'Est Method (Vehicle, Average, Observer Estimate)': 'Est_Method'
    })

    # Derive Final_Destination from Day's Route (e.g. "HRL-MSP-OMA-HRL")
    # Use the last airport code, unless it is MSP, in which case use the second to last.
    def _parse_final_destination(route):
        if not isinstance(route, str) or not route.strip():
            return None
        stops = [s.strip() for s in route.split('-') if s.strip()]
        if not stops:
            return None
        if len(stops) >= 2 and stops[-1].upper() == 'MSP':
            return stops[-2].upper()
        return stops[-1].upper()

    df_clean['Final_Destination'] = df_clean["Day’s Route"].apply(_parse_final_destination)

    # Calculate estimated detainees (total - observed)
    df_clean['Deportees_Estimated'] = df_clean['Deportees'] - df_clean['Deportee (observed)']

    # Filter to rows with non-null Deportees data
    non_null_detainees = df_clean[df_clean['Deportees'].notna()]

    # Create daily summary
    daily_summary = non_null_detainees.groupby(non_null_detainees['Date'].dt.date).agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum',
        'Est_Method': _format_est_methods
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
            'Deportees_Estimated': 0,
            'Est_Method': ''
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
        'Deportees_Estimated': 'sum',
        'Est_Method': _format_est_methods
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
        'Deportees_Estimated': 'sum',
        'Est_Method': _format_est_methods
    }).reset_index()

    # Sort ascending for horizontal bars (bottom-to-top reading)
    destination_totals = destination_totals.sort_values('Deportees', ascending=True)

    return destination_totals


def aggregate_detainees_by_final_destination(flight_df):
    """Aggregate detainees by final destination airport, split by observed vs estimated."""
    # Exclude null final destinations
    valid = flight_df[flight_df['Final_Destination'].notna()].copy()

    totals = valid.groupby('Final_Destination').agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum',
        'Est_Method': _format_est_methods
    }).reset_index()

    # Sort ascending for horizontal bars (bottom-to-top reading)
    totals = totals.sort_values('Deportees', ascending=True)

    return totals


def aggregate_detainees_by_tail(flight_df):
    """Aggregate detainees by aircraft tail number, split by observed vs estimated."""
    # Exclude null tail numbers
    valid = flight_df[flight_df['Tail'].notna()].copy()
    valid['Tail'] = valid['Tail'].str.strip()

    totals = valid.groupby('Tail').agg({
        'Deportees': 'sum',
        'Deportee (observed)': 'sum',
        'Deportees_Estimated': 'sum',
        'Est_Method': _format_est_methods
    }).reset_index()

    # Sort ascending for horizontal bars (bottom-to-top reading)
    totals = totals.sort_values('Deportees', ascending=True)

    return totals
