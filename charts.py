import plotly.graph_objects as go


# Key events shared across time-series charts
KEY_EVENTS = [
    {"date": "2025-12-04", "label": "Operation Metro Surge begins"},
    {"date": "2026-01-07", "label": "Killing of Renée Good"},
    {"date": "2026-01-24", "label": "Killing of Alex Pretti"},
    {"date": "2026-01-26", "label": "Bovino replaced by Homan"},
    {"date": "2026-02-04", "label": "700 agent drawdown"},
    {"date": "2026-02-12", "label": "Homan: operation ending"}
]


def _est_method_hover_text(data):
    """Build per-row hover text fragments for estimation methods.

    Returns a list of strings. Each entry is either empty or
    '<br>Estimation method: ...' ready to append in a hovertemplate.
    """
    if 'Est_Method' not in data.columns:
        return [''] * len(data)
    return [
        f'Method: {m}' if m else ''
        for m in data['Est_Method']
    ]


def _add_event_markers(fig, plot_data, max_y):
    """Add key event vertical lines and annotations to a time-series figure."""
    for event in KEY_EVENTS:
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


def create_bar_chart(daily_data, show_events=True):
    """Create an interactive stacked bar chart showing observed vs estimated detainees by day."""

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
        hovertemplate='Observed detainees: <b>%{y}</b><br>' +
                      'Total detainees: <b>%{customdata[1]}</b>' +
                      '<extra></extra>',
        customdata=list(zip(plot_data['DayOfWeek'], plot_data['Deportees']))
    ))

    # Add event markers if requested
    if show_events and not plot_data.empty:
        max_y = plot_data['Deportees'].max()
        _add_event_markers(fig, plot_data, max_y)

    # Add estimated detainees bar
    est_hover = _est_method_hover_text(plot_data)
    fig.add_trace(go.Bar(
        x=plot_data['FormattedDate'],
        y=plot_data['Deportees_Estimated'],
        name='Estimated',
        marker_color='#73b2cc',
        hovertemplate='<b>%{x} (%{customdata[0]})</b><br>' +
                      'Estimated detainees: <b>%{y}</b><br>' +
                      '%{customdata[1]}' +
                      '<extra></extra>',
        customdata=list(zip(plot_data['DayOfWeek'], est_hover))
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

    # Prepare data
    plot_data = data.copy()
    plot_data['FormattedDate'] = plot_data['Date'].dt.strftime('%Y-%m-%d')
    plot_data['DayOfWeek'] = plot_data['Date'].dt.strftime('%A')

    # Create figure
    fig = go.Figure()

    if stacked and observed_col and estimated_col:
        totals = plot_data[observed_col] + plot_data[estimated_col]
        est_hover = _est_method_hover_text(plot_data)

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
            customdata=list(zip(plot_data['DayOfWeek'], totals))
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
                          '%{customdata[2]}' +
                          '<extra></extra>',
            customdata=list(zip(plot_data['DayOfWeek'], totals, est_hover))
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
        _add_event_markers(fig, plot_data, max_y)

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
        totals = data[observed_col] + data[estimated_col]
        est_hover = _est_method_hover_text(data)

        # Add observed bar
        fig.add_trace(go.Bar(
            x=data[observed_col],
            y=data[category_col],
            orientation='h',
            name='Observed',
            marker_color='#2E86AB',
            hovertemplate='Observed (departing MSP): <b>%{x}</b><br>' +
                          'Total: <b>%{customdata[0]}</b>' +
                          '<extra></extra>',
            customdata=list(zip(totals))
        ))

        # Add estimated bar
        fig.add_trace(go.Bar(
            x=data[estimated_col],
            y=data[category_col],
            orientation='h',
            name='Estimated',
            marker_color='#73b2cc',
            hovertemplate='<b>%{y}</b><br>' +
                          'Estimated (departing MSP): <b>%{x}</b><br>' +
                          '%{customdata[1]}' +
                          '<extra></extra>',
            customdata=list(zip(totals, est_hover))
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
