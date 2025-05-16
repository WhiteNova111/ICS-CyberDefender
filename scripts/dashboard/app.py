import os
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, dash_table, callback
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Initialize the Dash app
app = Dash(__name__)
server = app.server

# Paths
data_folder = os.path.join(os.getcwd(), 'data', 'raw')
alerts_path = os.path.join(os.getcwd(), 'logs', 'alerts', 'anomaly.log')
raw_logs_path = os.path.join(os.getcwd(), 'logs', 'raw')

# Load raw datasets
datasets = {}
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

# Load anomalies log
def load_anomalies(path):
    if not os.path.isfile(path):
        return pd.DataFrame()
    records = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(',',3)
            if len(parts)<4: continue
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
                'reg0':r0,
                'reg1':r1,
                'score':score,
                'shap':shap
            })
    return pd.DataFrame(records)

# Load raw logs
def load_raw_logs():
    logs = {}
    if os.path.exists(raw_logs_path):
        for fname in os.listdir(raw_logs_path):
            if fname.endswith('.log'):
                try:
                    with open(os.path.join(raw_logs_path, fname), 'r') as f:
                        logs[fname] = f.readlines()
                except Exception as e:
                    print(f"Error loading {fname}: {e}")
    return logs

anomalies_df = load_anomalies(alerts_path)
raw_logs = load_raw_logs()

# Layout
first_dataset = list(datasets.keys())[0]
first_df = datasets[first_dataset]
default_start = first_df['timestamp'].min() if not first_df.empty else datetime(2024,1,1)
default_end = first_df['timestamp'].max() if not first_df.empty else datetime(2024,1,2)
app.layout = html.Div(style={'fontFamily':'Arial, sans-serif','margin':'20px'}, children=[
    html.H1("ICS Cyber-Defender Dashboard", style={'textAlign':'center'}),
    
    # Summary cards
    html.Div(style={'display':'flex','justifyContent':'space-around','marginBottom':'30px'}, children=[
        html.Div([
            html.H3('Datasets'), 
            html.P(f"{len(datasets)} loaded")
        ], style={'padding':'10px','border':'1px solid #ccc','borderRadius':'5px','width':'18%'}),
        html.Div([
            html.H3('Anomalies Total'), 
            html.P(f"{len(anomalies_df)} detected")
        ], style={'padding':'10px','border':'1px solid #ccc','borderRadius':'5px','width':'18%'}),
        html.Div([
            html.H3('Latest Anomaly'), 
            html.P(anomalies_df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S') if not anomalies_df.empty else 'None')
        ], style={'padding':'10px','border':'1px solid #ccc','borderRadius':'5px','width':'18%'}),
        html.Div([
            html.H3('Avg Anomaly Score'), 
            html.P(f"{anomalies_df['score'].mean():.3f}" if not anomalies_df.empty else 'N/A')
        ], style={'padding':'10px','border':'1px solid #ccc','borderRadius':'5px','width':'18%'})
    ]),

    # Controls
    html.Div(style={'display':'flex','marginBottom':'20px'}, children=[
        html.Div([
            html.Label("Select Dataset:"),
            dcc.Dropdown(id='dataset-dropdown', options=[{'label':k,'value':k} for k in datasets], value=first_dataset)
        ], style={'width':'30%'}),
        html.Div([
            html.Label("Time Range:"),
            dcc.DatePickerRange(
                id='date-range',
                start_date=default_start,
                end_date=default_end
            )
        ], style={'width':'30%','marginLeft':'20px'}),
        html.Div([
            html.Label("Visualization Options:"),
            dcc.Checklist(
                id='vis-options',
                options=[
                    {'label':'Show Anomalies','value':'anomalies'},
                    {'label':'Show Moving Average','value':'ma'},
                    {'label':'Show Thresholds','value':'thresholds'},
                    {'label':'Show Attack Periods','value':'attacks'}
                ],
                value=['anomalies', 'thresholds']
            )
        ], style={'width':'30%','marginLeft':'20px'})
    ]),

    # Time series
    dcc.Graph(id='time-series-graph'),

    # Statistics and Anomaly Details
    html.Div(style={'display':'flex','marginTop':'30px'}, children=[
        html.Div([
            html.H2('Dataset Statistics'),
            dash_table.DataTable(
                id='stats-table',
                columns=[
                    {'name':'Metric','id':'metric'},
                    {'name':'Value','id':'value'}
                ],
                style_table={'overflowX':'auto'}
            )
        ], style={'width':'30%','padding':'10px'}),
        html.Div([
            html.H2('Anomaly Details'),
            dash_table.DataTable(
                id='anomaly-table',
                columns=[{'name':c,'id':c} for c in anomalies_df.columns],
                data=anomalies_df.to_dict('records'),
                page_size=10,
                style_table={'overflowX':'auto','height':'300px','overflowY':'scroll'}
            )
        ], style={'width':'70%','padding':'10px'})
    ]),

    # Log Viewer Section
    html.Div([
        html.H2('Log Viewer', style={'marginTop':'30px'}),
        html.Div([
            html.Div([
                html.Label("Select Log File:"),
                dcc.Dropdown(
                    id='log-file-dropdown',
                    options=[{'label':k,'value':k} for k in raw_logs.keys()],
                    value=list(raw_logs.keys())[0] if raw_logs else None
                )
            ], style={'width':'30%'}),
            html.Div([
                html.Label("Search Logs:"),
                dcc.Input(
                    id='log-search',
                    type='text',
                    placeholder='Search in logs...',
                    style={'width':'100%'}
                )
            ], style={'width':'30%','marginLeft':'20px'})
        ], style={'display':'flex','marginBottom':'20px'}),
        html.Div([
            html.Div([
                html.H3('Raw Logs'),
                html.Div(
                    id='raw-logs-content',
                    style={
                        'height':'300px',
                        'overflowY':'scroll',
                        'backgroundColor':'#f8f9fa',
                        'padding':'10px',
                        'fontFamily':'monospace',
                        'whiteSpace':'pre-wrap'
                    }
                )
            ], style={'width':'50%','padding':'10px'}),
            html.Div([
                html.H3('Alert Logs'),
                html.Div(
                    id='alert-logs-content',
                    style={
                        'height':'300px',
                        'overflowY':'scroll',
                        'backgroundColor':'#f8f9fa',
                        'padding':'10px',
                        'fontFamily':'monospace',
                        'whiteSpace':'pre-wrap'
                    }
                )
            ], style={'width':'50%','padding':'10px'})
        ], style={'display':'flex'})
    ])
])

# Callbacks
@app.callback(
    Output('time-series-graph','figure'),
    Output('stats-table','data'),
    Input('dataset-dropdown','value'),
    Input('date-range','start_date'),
    Input('date-range','end_date'),
    Input('vis-options','value')
)
def update_dashboard(selected, start_date, end_date, options):
    df = datasets.get(selected, pd.DataFrame())
    if not df.empty:
        mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
        df = df.loc[mask]
    
    fig = go.Figure()
    
    if not df.empty:
        # Plot each numeric column with different colors
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        for i, col in enumerate(df.select_dtypes(include=['number']).columns):
            if col != 'timestamp':
                # Main line
                fig.add_trace(go.Scatter(
                    x=df['timestamp'], 
                    y=df[col], 
                    mode='lines', 
                    name=col,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
                
                if 'ma' in options:
                    # Add moving average
                    ma = df[col].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=ma,
                        mode='lines',
                        name=f'{col} MA',
                        line=dict(dash='dash', color=colors[i % len(colors)])
                    ))
                
                if 'thresholds' in options:
                    # Add thresholds
                    mean = df[col].mean()
                    std = df[col].std()
                    fig.add_hline(y=mean + 2*std, line_dash="dash", line_color="red", 
                                annotation_text="Upper Threshold", annotation_position="top right")
                    fig.add_hline(y=mean - 2*std, line_dash="dash", line_color="red",
                                annotation_text="Lower Threshold", annotation_position="bottom right")
                    fig.add_hline(y=mean, line_dash="dot", line_color="green",
                                annotation_text="Mean", annotation_position="top left")
    
    if 'anomalies' in options and not anomalies_df.empty:
        mask = (anomalies_df['timestamp'] >= start_date) & (anomalies_df['timestamp'] <= end_date)
        anom_df = anomalies_df.loc[mask]
        fig.add_trace(go.Scatter(
            x=anom_df['timestamp'],
            y=anom_df['reg0'],
            mode='markers',
            name='Anomaly',
            marker=dict(
                size=10,
                color='red',
                symbol='x',
                line=dict(width=2, color='black')
            )
        ))
    
    if 'attacks' in options and 'attack' in selected:
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
        title=f"Time Series: {selected}",
        xaxis_title='Time',
        yaxis_title='Value',
        template='plotly_white',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        height=600
    )
    
    # Calculate statistics
    stats = []
    if not df.empty:
        for col in df.select_dtypes(include=['number']).columns:
            if col != 'timestamp':
                stats.extend([
                    {'metric':f'{col} Mean', 'value':f"{df[col].mean():.2f}"},
                    {'metric':f'{col} Std', 'value':f"{df[col].std():.2f}"},
                    {'metric':f'{col} Min', 'value':f"{df[col].min():.2f}"},
                    {'metric':f'{col} Max', 'value':f"{df[col].max():.2f}"},
                    {'metric':f'{col} Range', 'value':f"{df[col].max() - df[col].min():.2f}"}
                ])
    else:
        stats = [{'metric': 'No data in selected range', 'value': ''}]
    
    return fig, stats

@app.callback(
    Output('raw-logs-content', 'children'),
    Output('alert-logs-content', 'children'),
    Input('log-file-dropdown', 'value'),
    Input('log-search', 'value')
)
def update_logs(selected_log, search_term):
    # Update raw logs
    raw_content = ""
    if selected_log and selected_log in raw_logs:
        logs = raw_logs[selected_log]
        if search_term:
            logs = [line for line in logs if search_term.lower() in line.lower()]
        raw_content = "".join(logs)
    
    # Update alert logs
    alert_content = ""
    if os.path.exists(alerts_path):
        with open(alerts_path, 'r') as f:
            alerts = f.readlines()
            if search_term:
                alerts = [line for line in alerts if search_term.lower() in line.lower()]
            alert_content = "".join(alerts)
    
    return raw_content, alert_content

if __name__=='__main__':
    app.run(debug=True, port=8050)
