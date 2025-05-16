import os
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, State, dash_table, callback, callback_context
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
import json
import base64
import io

# Initialize the Dash app with Bootstrap for better styling
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# Paths
data_folder = os.path.join(os.getcwd(), 'data', 'raw')
alerts_path = os.path.join(os.getcwd(), 'logs', 'alerts', 'anomaly.log')

# Ensure directories exist
os.makedirs(data_folder, exist_ok=True)
os.makedirs(os.path.dirname(alerts_path), exist_ok=True)

# Function to load data from CSV files
def load_datasets():
    datasets = {}
    if os.path.exists(data_folder):
        for fname in sorted(os.listdir(data_folder)):
            if fname.endswith('.csv'):
                name = os.path.splitext(fname)[0]
                try:
                    df = pd.read_csv(os.path.join(data_folder, fname))
                    # Create realistic timestamps based on file name
                    if 'baseline' in name:
                        start_time = datetime(2024, 1, 1)
                    elif 'attack' in name:
                        start_time = datetime(2024, 1, 1, 12)  # Attacks start at noon
                    else:
                        start_time = datetime(2024, 1, 1, 8)  # Other scenarios start at 8 AM
                        
                    df['timestamp'] = pd.date_range(start=start_time, periods=len(df), freq='s')
                    datasets[name] = df
                except Exception as e:
                    print(f"Error loading {fname}: {e}")
                    datasets[name] = pd.DataFrame()
    return datasets

# Load anomalies log
def load_anomalies(path):
    if not os.path.isfile(path):
        return pd.DataFrame(columns=['timestamp', 'reg0', 'reg1', 'score', 'shap'])
    
    records = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(',', 3)
            if len(parts) < 4: continue
            ts, vals, score, shap = parts
            try: ts = float(ts)
            except: continue
            vals = vals.strip().lstrip('[').rstrip(']').split(',')
            try:
                r0 = float(vals[0]); r1 = float(vals[1])
            except: r0=r1=None
            try: score = float(score.strip().strip('[]'))
            except: score=None
            records.append({
                'timestamp': datetime.fromtimestamp(ts),
                'reg0': r0,
                'reg1': r1,
                'score': score,
                'shap': shap
            })
    return pd.DataFrame(records)

# Load initial data
datasets = load_datasets()
anomalies_df = load_anomalies(alerts_path)

# Function to parse uploaded files
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if filename.endswith('.csv'):
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            
            # Create timestamps
            name = os.path.splitext(filename)[0]
            if 'baseline' in name.lower():
                start_time = datetime(2024, 1, 1)
            elif 'attack' in name.lower():
                start_time = datetime(2024, 1, 1, 12)
            else:
                start_time = datetime(2024, 1, 1, 8)
                
            df['timestamp'] = pd.date_range(start=start_time, periods=len(df), freq='s')
            
            # Save the file locally
            os.makedirs(data_folder, exist_ok=True)
            df.to_csv(os.path.join(data_folder, filename), index=False)
            
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print(e)
        return pd.DataFrame()

# Function to generate dataset info card
def create_info_card(title, value, color="primary"):
    return dbc.Card(
        [
            dbc.CardHeader(title, className="text-white bg-" + color),
            dbc.CardBody(
                [
                    html.H3(value, className="card-title text-center"),
                ]
            ),
        ],
        className="mb-4"
    )

# Function to create navigation tabs
def create_tabs():
    return dbc.Tabs(
        [
            dbc.Tab(label="Overview", tab_id="tab-overview"),
            dbc.Tab(label="Time Series Analysis", tab_id="tab-timeseries"),
            dbc.Tab(label="Anomaly Detection", tab_id="tab-anomalies"),
            dbc.Tab(label="Statistical Analysis", tab_id="tab-stats"),
            dbc.Tab(label="Data Management", tab_id="tab-data"),
        ],
        id="tabs",
        active_tab="tab-overview",
        className="mb-3"
    )

# Layout
app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col([
            html.H1("ICS Cyber-Defender Dashboard", className="display-4 text-center my-4"),
            html.Hr()
        ])
    ]),
    
    # Navigation
    dbc.Row([
        dbc.Col([
            create_tabs()
        ])
    ]),
    
    # Content
    html.Div(id="tab-content"),
    
    # Store for datasets and current selection
    dcc.Store(id='datasets-store'),
    dcc.Store(id='current-dataset-store'),
    dcc.Store(id='anomalies-store'),
    
    # Interval for auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=300 * 1000,  # refresh every 5 minutes (300 seconds)
        n_intervals=0
    ),
    
    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("ICS Cyber-Defender Dashboard © 2025", className="text-center text-muted"),
        ])
    ]),

    # Add this to your layout, e.g. after the navigation
    html.Div(id="global-error-message", style={"color": "red", "fontWeight": "bold"}),
], style={"backgroundColor": "#f8f9fa"})

# Callbacks

# Store datasets in browser on page load
@app.callback(
    Output('datasets-store', 'data'),
    Output('anomalies-store', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_stores(n):
    datasets = load_datasets()
    anomalies_df = load_anomalies(alerts_path)
    
    # Convert datasets to JSON-serializable format
    datasets_json = {}
    for name, df in datasets.items():
        # Convert timestamps to string for JSON serialization
        df_copy = df.copy()
        df_copy['timestamp'] = df_copy['timestamp'].astype(str)
        datasets_json[name] = df_copy.to_dict('records')
    
    # Convert anomalies to JSON-serializable format
    anomalies_json = anomalies_df.copy()
    if not anomalies_json.empty:
        anomalies_json['timestamp'] = anomalies_json['timestamp'].astype(str)
    
    return datasets_json, anomalies_json.to_dict('records')

# Handle file uploads
@app.callback(
    Output('datasets-store', 'data', allow_duplicate=True),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('datasets-store', 'data'),
    prevent_initial_call=True
)
def update_output(list_of_contents, list_of_filenames, existing_datasets):
    if list_of_contents is None:
        return existing_datasets
        
    # Process each uploaded file
    for content, filename in zip(list_of_contents, list_of_filenames):
        df = parse_contents(content, filename)
        if not df.empty:
            name = os.path.splitext(filename)[0]
            
            # Convert timestamps to string for JSON serialization
            df_copy = df.copy()
            df_copy['timestamp'] = df_copy['timestamp'].astype(str)
            
            # Add to existing datasets
            existing_datasets[name] = df_copy.to_dict('records')
            
    return existing_datasets

# Tab content router
@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'active_tab'),
    Input('datasets-store', 'data'),
    Input('anomalies-store', 'data')
)
def render_tab_content(active_tab, datasets_json, anomalies_json):
    # Convert from JSON back to dataframes
    datasets = {}
    for name, records in datasets_json.items():
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        datasets[name] = df
    
    anomalies_df = pd.DataFrame(anomalies_json)
    if not anomalies_df.empty and 'timestamp' in anomalies_df.columns:
        anomalies_df['timestamp'] = pd.to_datetime(anomalies_df['timestamp'])
    
    # Return appropriate content based on active tab
    if active_tab == "tab-overview":
        return render_overview_tab(datasets, anomalies_df)
    elif active_tab == "tab-timeseries":
        return render_timeseries_tab(datasets, anomalies_df)
    elif active_tab == "tab-anomalies":
        return render_anomalies_tab(datasets, anomalies_df)
    elif active_tab == "tab-stats":
        return render_stats_tab(datasets)
    elif active_tab == "tab-data":
        return render_data_tab(datasets)
    
    # Default case
    return html.P("This tab is not yet implemented")

# Overview Tab
def render_overview_tab(datasets, anomalies_df):
    # Calculate summary stats
    total_datasets = len(datasets)
    total_datapoints = sum(len(df) for df in datasets.values())
    total_anomalies = len(anomalies_df)
    
    # Latest anomaly time
    latest_anomaly = "None"
    if not anomalies_df.empty:
        latest_anomaly = anomalies_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
    
    # Average anomaly score
    avg_anomaly_score = "N/A"
    if not anomalies_df.empty and 'score' in anomalies_df.columns:
        avg_anomaly_score = f"{anomalies_df['score'].mean():.3f}"
    
    # Create layout
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("System Overview", className="mb-4")
            ])
        ]),
        
        # Info cards
        dbc.Row([
            dbc.Col([
                create_info_card("Datasets", f"{total_datasets}", "primary")
            ], width=3),
            dbc.Col([
                create_info_card("Total Data Points", f"{total_datapoints:,}", "info")
            ], width=3),
            dbc.Col([
                create_info_card("Anomalies Detected", f"{total_anomalies}", "warning")
            ], width=3),
            dbc.Col([
                create_info_card("Avg. Anomaly Score", avg_anomaly_score, "danger")
            ], width=3)
        ]),
        
        # Quick visualization
        dbc.Row([
            dbc.Col([
                html.H3("System Status Timeline", className="mb-3"),
                dcc.Graph(id="overview-timeline", figure=generate_overview_timeline(datasets, anomalies_df))
            ], width=12, className="mb-4")
        ]),
        
        # Recent anomalies
        dbc.Row([
            dbc.Col([
                html.H3("Recent Anomalies", className="mb-3"),
                generate_anomalies_table(anomalies_df)
            ], width=6),
            dbc.Col([
                html.H3("Anomaly Distribution", className="mb-3"),
                dcc.Graph(id="anomaly-distribution", figure=generate_anomaly_distribution(anomalies_df))
            ], width=6)
        ])
    ])

# Time Series Tab
def render_timeseries_tab(datasets, anomalies_df):
    # Create dropdown options
    dataset_options = [{'label': name, 'value': name} for name in datasets.keys()]
    
    # Get default dates
    default_start = None
    default_end = None
    
    # Use first dataset for default dates if available
    if dataset_options:
        first_dataset = datasets[dataset_options[0]['value']]
        if not first_dataset.empty and 'timestamp' in first_dataset.columns:
            default_start = first_dataset['timestamp'].min()
            default_end = first_dataset['timestamp'].max()
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Time Series Analysis", className="mb-4")
            ])
        ]),
        
        # Controls
        dbc.Row([
            dbc.Col([
                html.Label("Select Dataset:"),
                dcc.Dropdown(
                    id='ts-dataset-dropdown',
                    options=dataset_options,
                    value=dataset_options[0]['value'] if dataset_options else None,
                    className="mb-3"
                )
            ], width=3),
            dbc.Col([
                html.Label("Time Range:"),
                dcc.DatePickerRange(
                    id='ts-date-range',
                    start_date=default_start,
                    end_date=default_end,
                    className="mb-3"
                )
            ], width=4),
            dbc.Col([
                html.Label("Visualization Options:"),
                dbc.Checklist(
                    id='ts-vis-options',
                    options=[
                        {'label': ' Show Anomalies', 'value': 'anomalies'},
                        {'label': ' Show Moving Average', 'value': 'ma'},
                        {'label': ' Show Thresholds', 'value': 'thresholds'},
                        {'label': ' Show Attack Periods', 'value': 'attacks'}
                    ],
                    value=['anomalies', 'thresholds'],
                    inline=True,
                    className="mb-3"
                )
            ], width=5)
        ]),
        
        # Time series graph
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='timeseries-graph', style={'height': '600px'})
            ], width=12)
        ]),
        
        # Statistics
        dbc.Row([
            dbc.Col([
                html.H3("Dataset Statistics", className="mt-4 mb-3"),
                dash_table.DataTable(
                    id='ts-stats-table',
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px'
                    }
                )
            ], width=12)
        ])
    ])

# Anomalies Tab
def render_anomalies_tab(datasets, anomalies_df):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Anomaly Detection Analysis", className="mb-4")
            ])
        ]),
        
        # Anomaly timeline & distribution
        dbc.Row([
            dbc.Col([
                html.H3("Anomaly Timeline", className="mb-3"),
                dcc.Graph(
                    id='anomaly-timeline',
                    figure=generate_anomaly_timeline(anomalies_df),
                    style={'height': '400px'}
                )
            ], width=8),
            dbc.Col([
                html.H3("Score Distribution", className="mb-3"),
                dcc.Graph(
                    id='score-histogram',
                    figure=generate_score_histogram(anomalies_df),
                    style={'height': '400px'}
                )
            ], width=4)
        ]),
        
        # Detailed table
        dbc.Row([
            dbc.Col([
                html.H3("Anomaly Details", className="mt-4 mb-3"),
                dash_table.DataTable(
                    id='anomaly-detail-table',
                    columns=[{'name': c, 'id': c} for c in anomalies_df.columns if c != 'shap'],
                    data=anomalies_df.to_dict('records') if not anomalies_df.empty else [],
                    page_size=10,
                    filter_action="native",
                    sort_action="native",
                    sort_mode="multi",
                    style_table={'overflowX': 'auto', 'height': '400px', 'overflowY': 'auto'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px'
                    }
                )
            ], width=12)
        ]),
        
        # SHAP values analysis (if available)
        dbc.Row([
            dbc.Col([
                html.H3("Feature Importance (SHAP Values)", className="mt-4 mb-3"),
                dcc.Graph(
                    id='shap-analysis',
                    figure=generate_shap_analysis(anomalies_df),
                    style={'height': '400px'}
                )
            ], width=12)
        ])
    ])

# Stats Tab
def render_stats_tab(datasets):
    # Create dropdown options
    dataset_options = [{'label': name, 'value': name} for name in datasets.keys()]
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Statistical Analysis", className="mb-4")
            ])
        ]),
        
        # Dataset selection
        dbc.Row([
            dbc.Col([
                html.Label("Select Dataset:"),
                dcc.Dropdown(
                    id='stats-dataset-dropdown',
                    options=dataset_options,
                    value=dataset_options[0]['value'] if dataset_options else None,
                    className="mb-3"
                ),
                html.Hr()
            ], width=4)
        ]),
        
        # Summary statistics
        dbc.Row([
            dbc.Col([
                html.H3("Summary Statistics", className="mb-3"),
                html.Div(id="stats-summary-tables")
            ], width=12)
        ]),
        
        # Visualizations
        dbc.Row([
            dbc.Col([
                html.H3("Distribution Analysis", className="mt-4 mb-3"),
                dcc.Graph(id='stats-distribution')
            ], width=6),
            dbc.Col([
                html.H3("Correlation Analysis", className="mt-4 mb-3"),
                dcc.Graph(id='stats-correlation')
            ], width=6)
        ])
    ])

# Data Management Tab
def render_data_tab(datasets):
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("Data Management", className="mb-4")
            ])
        ]),
        
        # Upload new data
        dbc.Row([
            dbc.Col([
                html.H3("Upload Data Files", className="mb-3"),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    multiple=True
                ),
                html.Div(id='upload-output', className="mt-3")
            ], width=12)
        ]),
        
        # Available datasets
        dbc.Row([
            dbc.Col([
                html.H3("Available Datasets", className="mt-4 mb-3"),
                html.Div(id="available-datasets")
            ], width=12)
        ])
    ])

# Additional callbacks for specific tab functionality

# Time Series Analysis
@app.callback(
    Output('timeseries-graph', 'figure'),
    Output('ts-stats-table', 'data'),
    Output('ts-stats-table', 'columns'),
    Input('ts-dataset-dropdown', 'value'),
    Input('ts-date-range', 'start_date'),
    Input('ts-date-range', 'end_date'),
    Input('ts-vis-options', 'value'),
    State('datasets-store', 'data'),
    State('anomalies-store', 'data')
)
def update_timeseries(selected, start_date, end_date, options, datasets_json, anomalies_json):
    # Convert from JSON back to dataframes
    datasets = {}
    for name, records in datasets_json.items():
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        datasets[name] = df
    
    anomalies_df = pd.DataFrame(anomalies_json)
    if not anomalies_df.empty and 'timestamp' in anomalies_df.columns:
        anomalies_df['timestamp'] = pd.to_datetime(anomalies_df['timestamp'])
    
    df = datasets.get(selected, pd.DataFrame())
    
    # Create empty defaults
    fig = go.Figure()
    stats_data = []
    stats_columns = [{'name': 'Metric', 'id': 'metric'}, {'name': 'Value', 'id': 'value'}]
    
    if not df.empty:
        if start_date and end_date:
            mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
            df = df.loc[mask]
        
        # Plot each numeric column with different colors
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # First pass to count how many columns to see if we need secondary y-axis
        numeric_cols = df.select_dtypes(include=['number']).columns
        numeric_cols = [col for col in numeric_cols if col != 'timestamp']
        
        use_secondary = len(numeric_cols) > 1
        secondary_start = len(numeric_cols) // 2 if use_secondary else len(numeric_cols)
        
        for i, col in enumerate(numeric_cols):
            # Determine if this column should use secondary y-axis
            use_secondary_axis = i >= secondary_start if use_secondary else False
            
            # Main line
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'], 
                    y=df[col], 
                    mode='lines', 
                    name=col,
                    line=dict(color=colors[i % len(colors)], width=2)
                ),
                secondary_y=use_secondary_axis
            )
            
            if 'ma' in options:
                # Add moving average
                ma = df[col].rolling(window=20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=ma,
                        mode='lines',
                        name=f'{col} MA',
                        line=dict(dash='dash', color=colors[i % len(colors)])
                    ),
                    secondary_y=use_secondary_axis
                )
            
            if 'thresholds' in options:
                # Add thresholds
                mean = df[col].mean()
                std = df[col].std()
                
                fig.add_trace(
                    go.Scatter(
                        x=[df['timestamp'].min(), df['timestamp'].max()],
                        y=[mean + 2*std, mean + 2*std],
                        mode='lines',
                        name=f'{col} Upper Threshold',
                        line=dict(dash='dash', color=colors[i % len(colors)]),
                        showlegend=False
                    ),
                    secondary_y=use_secondary_axis
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=[df['timestamp'].min(), df['timestamp'].max()],
                        y=[mean - 2*std, mean - 2*std],
                        mode='lines',
                        name=f'{col} Lower Threshold',
                        line=dict(dash='dash', color=colors[i % len(colors)]),
                        showlegend=False
                    ),
                    secondary_y=use_secondary_axis
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=[df['timestamp'].min(), df['timestamp'].max()],
                        y=[mean, mean],
                        mode='lines',
                        name=f'{col} Mean',
                        line=dict(dash='dot', color=colors[i % len(colors)]),
                        showlegend=False
                    ),
                    secondary_y=use_secondary_axis
                )
        
        if 'anomalies' in options and not anomalies_df.empty:
            if start_date and end_date:
                mask = (anomalies_df['timestamp'] >= start_date) & (anomalies_df['timestamp'] <= end_date)
                anom_df = anomalies_df.loc[mask]
                
                if not anom_df.empty:
                    # Add anomalies as markers
                    fig.add_trace(
                        go.Scatter(
                            x=anom_df['timestamp'],
                            y=anom_df['reg0'],
                            mode='markers',
                            name='Anomalies',
                            marker=dict(
                                size=10,
                                color='red',
                                symbol='x',
                                line=dict(width=2, color='DarkSlateGrey')
                            )
                        ),
                        secondary_y=False
                    )
        
        if 'attacks' in options and 'attack' in selected.lower():
            # Add attack period shading
            attack_start = df['timestamp'].min() + timedelta(minutes=30)
            attack_end = attack_start + timedelta(minutes=15)
            
            fig.add_vrect(
                x0=attack_start,
                x1=attack_end,
                fillcolor="red",
                opacity=0.2,
                layer="below",
                line_width=0,
                annotation_text="Attack Period",
                annotation_position="top left"
            )
        
        fig.update_layout(
            title=f"Time Series Analysis: {selected}",
            xaxis_title='Time',
            yaxis_title='Value',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=50, b=50),
            height=600
        )
        
        # Update axis titles
        if use_secondary:
            fig.update_yaxes(title_text="Primary Variables", secondary_y=False)
            fig.update_yaxes(title_text="Secondary Variables", secondary_y=True)
        
        # Calculate statistics
        for col in numeric_cols:
            stats_data.extend([
                {'metric': f'{col} Mean', 'value': f"{df[col].mean():.4f}"},
                {'metric': f'{col} Std Dev', 'value': f"{df[col].std():.4f}"},
                {'metric': f'{col} Min', 'value': f"{df[col].min():.4f}"},
                {'metric': f'{col} Max', 'value': f"{df[col].max():.4f}"},
                {'metric': f'{col} Range', 'value': f"{df[col].max() - df[col].min():.4f}"},
                {'metric': f'{col} Median', 'value': f"{df[col].median():.4f}"}
            ])
    
    return fig, stats_data, stats_columns

# Statistics Tab callbacks
@app.callback(
    Output('stats-summary-tables', 'children'),
    Output('stats-distribution', 'figure'),
    Output('stats-correlation', 'figure'),
    Input('stats-dataset-dropdown', 'value'),
    State('datasets-store', 'data')
)
def update_stats_tab(selected, datasets_json):
    # Convert from JSON back to dataframes
    datasets = {}
    for name, records in datasets_json.items():
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        datasets[name] = df
    
    df = datasets.get(selected, pd.DataFrame())
    
    # Default empty returns
    summary_tables = html.Div("No data available")
    dist_fig = go.Figure()
    corr_fig = go.Figure()
    
    if not df.empty:
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        numeric_cols = [col for col in numeric_cols if col != 'timestamp']
        
        if numeric_cols:
            # Create summary statistics
            summary_tables = []
            
            # Descriptive statistics
            desc_stats = df[numeric_cols].describe().reset_index()
            desc_stats = desc_stats.round(4)  # Round to 4 decimal places
            
            summary_tables.append(
                html.Div([
                    html.H4("Descriptive Statistics"),
                    dash_table.DataTable(
                        data=desc_stats.to_dict('records'),
                        columns=[{'name': str(col), 'id': str(col)} for col in desc_stats.columns],
                        style_table={'overflowX': 'auto'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px'
                        }
                    )
                ], className="mb-4")
            )
            
            # Additional statistics
            additional_stats = pd.DataFrame({
                'Variable': numeric_cols,
                'Skewness': [df[col].skew() for col in numeric_cols],
                'Kurtosis': [df[col].kurtosis() for col in numeric_cols],
                'Missing Values': [df[col].isna().sum() for col in numeric_cols],
                'Missing (%)': [100 * df[col].isna().sum() / len(df) for col in numeric_cols]
            }).round(4)
            
            summary_tables.append(
                html.Div([
                    html.H4("Additional Statistics"),
                    dash_table.DataTable(
                        data=additional_stats.to_dict('records'),
                        columns=[{'name': str(col), 'id': str(col)} for col in additional_stats.columns],
                        style_table={'overflowX': 'auto'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px'
                        }
                    )
                ], className="mb-4")
            )
            
            # Create distribution plot
            dist_fig = make_subplots(rows=len(numeric_cols), cols=1, 
                                   subplot_titles=[f"Distribution of {col}" for col in numeric_cols],
                                   vertical_spacing=0.05)
            
            for i, col in enumerate(numeric_cols):
                # Add histogram
                dist_fig.add_trace(
                    go.Histogram(
                        x=df[col],
                        name=col,
                        marker_color='rgba(0, 123, 255, 0.6)',
                        opacity=0.8,
                        autobinx=True
                    ),
                    row=i+1, col=1
                )
                
                # Add KDE (estimated using histogram)
                hist, bin_edges = np.histogram(df[col].dropna(), bins='auto', density=True)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                
                if len(bin_centers) > 1:  # Ensure we have enough points for line
                    dist_fig.add_trace(
                        go.Scatter(
                            x=bin_centers,
                            y=hist,
                            mode='lines',
                            name=f"{col} density",
                            line=dict(color='rgba(220, 53, 69, 0.8)', width=2),
                            showlegend=False
                        ),
                        row=i+1, col=1
                    )
            
            dist_fig.update_layout(
                height=250 * len(numeric_cols),
                showlegend=False,
                template='plotly_white',
                title_text=f"Distribution Analysis for {selected}",
                margin=dict(l=50, r=50, t=50, b=20)
            )
            
            # Create correlation heatmap
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr().round(3)
                corr_fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    zmin=-1, zmax=1,
                    colorscale='RdBu',
                    colorbar=dict(title='Correlation'),
                    text=corr_matrix.values.round(3),
                    texttemplate="%{text}",
                    hoverinfo='text',
                    hovertext=[[f'Correlation between {x} and {y}: {z}' 
                                for z, y in zip(corr_matrix.values[i], corr_matrix.columns)]
                                for i, x in enumerate(corr_matrix.index)]
                ))
                
                corr_fig.update_layout(
                    height=500,
                    title_text=f"Correlation Matrix for {selected}",
                    template='plotly_white',
                    margin=dict(l=50, r=50, t=50, b=50)
                )
            else:
                corr_fig = go.Figure()
                corr_fig.update_layout(
                    title="Correlation analysis requires multiple numeric variables",
                    template='plotly_white',
                    height=500
                )
            
    return summary_tables, dist_fig, corr_fig

# Data Management Tab callbacks
@app.callback(
    Output('available-datasets', 'children'),
    Input('datasets-store', 'data')
)
def update_available_datasets(datasets_json):
    if not datasets_json:
        return html.P("No datasets available.")
    
    # Create a card for each dataset
    dataset_cards = []
    
    for name, records in datasets_json.items():
        df = pd.DataFrame(records)
        
        # Get basic info
        num_records = len(df)
        num_columns = len(df.columns)
        columns = ", ".join(df.columns)
        
        # Create card
        card = dbc.Card([
            dbc.CardHeader(name, className="bg-primary text-white"),
            dbc.CardBody([
                html.P(f"Records: {num_records}", className="card-text"),
                html.P(f"Columns: {num_columns}", className="card-text"),
                html.P(f"Variables: {columns}", className="card-text"),
                dbc.Button("View Sample", id={'type': 'view-dataset', 'index': name}, 
                           color="primary", className="mt-2")
            ])
        ], className="mb-3")
        
        dataset_cards.append(dbc.Col(card, width=4))
    
    # Arrange cards in rows
    rows = []
    for i in range(0, len(dataset_cards), 3):
        row = dbc.Row(dataset_cards[i:i+3], className="mb-4")
        rows.append(row)
    
    return html.Div(rows)

# Helper functions for visualization

def generate_overview_timeline(datasets, anomalies_df):
    """Generate overview timeline with dataset availability and anomalies"""
    fig = go.Figure()
    
    # Plot dataset availability periods
    colors = px.colors.qualitative.Plotly
    
    for i, (name, df) in enumerate(datasets.items()):
        if not df.empty and 'timestamp' in df.columns:
            color = colors[i % len(colors)]
            start_time = df['timestamp'].min()
            end_time = df['timestamp'].max()
            
            # Add dataset period as a rectangle
            fig.add_trace(go.Scatter(
                x=[start_time, end_time],
                y=[i, i],
                mode='lines',
                line=dict(color=color, width=10),
                name=name,
                hoverinfo='text',
                hovertext=f"{name}: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            ))
    
    # Add anomalies as markers
    if not anomalies_df.empty and 'timestamp' in anomalies_df.columns:
        fig.add_trace(go.Scatter(
            x=anomalies_df['timestamp'],
            y=[-0.5] * len(anomalies_df),  # Plot below datasets
            mode='markers',
            marker=dict(
                symbol='star',
                size=12,
                color='red',
                line=dict(width=1, color='DarkSlateGrey')
            ),
            name='Anomalies',
            hoverinfo='text',
            hovertext=[f"Anomaly at {ts.strftime('%Y-%m-%d %H:%M:%S')}<br>Score: {score:.3f}" 
                      for ts, score in zip(anomalies_df['timestamp'], anomalies_df['score'])]
        ))
    
    # Layout
    fig.update_layout(
        title="System Timeline Overview",
        xaxis_title="Time",
        yaxis_title="",
        template='plotly_white',
        height=300,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(len(datasets))),
            ticktext=list(datasets.keys()),
            showgrid=False
        ),
        margin=dict(l=50, r=50, t=50, b=20)
    )
    
    return fig

def generate_anomalies_table(anomalies_df):
    """Generate a table with recent anomalies"""
    if anomalies_df.empty:
        return html.P("No anomalies detected.")
    
    # Take most recent anomalies
    recent_df = anomalies_df.sort_values('timestamp', ascending=False).head(5)
    
    # Format the data
    recent_df = recent_df.copy()
    recent_df['timestamp'] = recent_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create table columns (excluding SHAP values)
    columns = [{'name': c, 'id': c} for c in recent_df.columns if c != 'shap']
    
    return dash_table.DataTable(
        id='recent-anomalies-table',
        columns=columns,
        data=recent_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '10px'
        }
    )

def generate_anomaly_distribution(anomalies_df):
    """Generate score distribution for anomalies"""
    fig = go.Figure()
    
    if not anomalies_df.empty and 'score' in anomalies_df.columns:
        # Create histogram
        fig.add_trace(go.Histogram(
            x=anomalies_df['score'],
            marker_color='rgba(255, 0, 0, 0.7)',
            opacity=0.8,
            name='Anomaly Scores',
            autobinx=True
        ))
    
    # Layout
    fig.update_layout(
        title="Anomaly Score Distribution",
        xaxis_title="Score",
        yaxis_title="Frequency",
        template='plotly_white',
        height=300,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=20)
    )
    
    return fig

def generate_anomaly_timeline(anomalies_df):
    """Generate timeline of anomaly occurrences with scores"""
    fig = go.Figure()
    
    if not anomalies_df.empty and 'timestamp' in anomalies_df.columns and 'score' in anomalies_df.columns:
        # Sort by timestamp
        sorted_df = anomalies_df.sort_values('timestamp')
        
        # Create scatter plot
        fig.add_trace(go.Scatter(
            x=sorted_df['timestamp'],
            y=sorted_df['score'],
            mode='markers',
            marker=dict(
                size=sorted_df['score'] * 5,  # Size proportional to score
                color=sorted_df['score'],
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title='Score'),
                line=dict(width=1, color='DarkSlateGrey')
            ),
            name='Anomalies',
            hoverinfo='text',
            hovertext=[f"Time: {ts.strftime('%Y-%m-%d %H:%M:%S')}<br>Score: {score:.3f}<br>Reg0: {r0:.2f}, Reg1: {r1:.2f}" 
                      for ts, score, r0, r1 in zip(sorted_df['timestamp'], sorted_df['score'], 
                                                  sorted_df['reg0'], sorted_df['reg1'])]
        ))
    
    # Layout
    fig.update_layout(
        title="Anomaly Detection Timeline",
        xaxis_title="Time",
        yaxis_title="Anomaly Score",
        template='plotly_white',
        height=400,
        showlegend=False,
        margin=dict(l=50, r=50, t=50, b=20)
    )
    
    return fig

def generate_score_histogram(anomalies_df):
    """Generate detailed histogram of anomaly scores"""
    fig = go.Figure()
    
    if not anomalies_df.empty and 'score' in anomalies_df.columns:
        # Create histogram with more detail than simple distribution
        fig.add_trace(go.Histogram(
            x=anomalies_df['score'],
            marker=dict(
                color='rgba(255, 0, 0, 0.7)',
                line=dict(color='rgba(255, 0, 0, 1)', width=1)
            ),
            opacity=0.8,
            name='Anomaly Scores',
            autobinx=True
        ))
        
        # Add KDE overlay (estimated using histogram)
        hist, bin_edges = np.histogram(anomalies_df['score'].dropna(), bins='auto', density=True)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        if len(bin_centers) > 1:  # Ensure we have enough points for line
            fig.add_trace(go.Scatter(
                x=bin_centers,
                y=hist,
                mode='lines',
                line=dict(color='rgba(0, 0, 0, 0.8)', width=2),
                name='Density'
            ))
        
        # Add vertical line for mean score
        mean_score = anomalies_df['score'].mean()
        fig.add_vline(
            x=mean_score,
            line_dash="dash",
            line_color="black",
            annotation_text=f"Mean: {mean_score:.3f}",
            annotation_position="top right"
        )
    
    # Layout
    fig.update_layout(
        title="Anomaly Score Distribution",
        xaxis_title="Score",
        yaxis_title="Frequency",
        template='plotly_white',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=50, b=20)
    )
    
    return fig

def generate_shap_analysis(anomalies_df):
    """Generate SHAP value analysis if available"""
    fig = go.Figure()
    
    # Check if we have shap values to analyze
    if not anomalies_df.empty and 'shap' in anomalies_df.columns:
        # Try to parse SHAP values - this is just a placeholder
        # In a real implementation, you'd parse the actual SHAP values from the column
        
        # Create dummy data for example
        features = ['Feature1', 'Feature2', 'Feature3', 'Feature4']
        importance = [0.8, 0.5, 0.3, 0.2]
        
        # Sort by importance
        sorted_indices = np.argsort(importance)
        sorted_features = [features[i] for i in sorted_indices]
        sorted_importance = [importance[i] for i in sorted_indices]
        
        fig.add_trace(go.Bar(
            y=sorted_features,
            x=sorted_importance,
            orientation='h',
            marker=dict(
                color=sorted_importance,
                colorscale='Reds',
                line=dict(width=1, color='DarkSlateGrey')
            )
        ))
    else:
        # No SHAP values available
        fig.add_annotation(
            text="SHAP values not available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
    
    # Layout
    fig.update_layout(
        title="Feature Importance (SHAP Values)",
        xaxis_title="Impact on Model Output",
        yaxis_title="Feature",
        template='plotly_white',
        height=400,
        margin=dict(l=150, r=50, t=50, b=20)
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True, port=8050)