import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import numpy as np
from datetime import datetime
from serial import Serial
from collections import deque
from time import sleep
from pandas import Series
from threading import Thread, Event

# ser = Serial("COM4", 115200, timeout=0.1)
# sleep(1.5)
readings = [deque(maxlen=25) for _ in range(12)]
timestamps = deque(maxlen=25)


def server_tick(event):
    """This function is used to generate the 1s interval to sample the instruments. Doing it
        it in the background of the server prevents possible collisions if there is more than one
        client viewing the dashboard. It also allows the instruments to still be read and logged
        even when no clients are connected.

    Args:
        event (Event): Triggers arduino to read sensors
    """

    while True:

        sleep(1)  # Update every 1 second
        timestamps.append(datetime.now())
        event.set()
        print("tick", datetime.now().strftime("%H:%M:%S:%f"))


def read_sensors(event):

    while True:
        event.wait()
        # ser.write(b"R")
        # values = ser.readline().strip().decode().split()
        values = np.random.uniform(0, 1, 12)
        for i in range(12):
            readings[i].append(float(values[i]))
        event.clear()


event_read = Event()

thread0 = Thread(target=server_tick, args=(event_read,), daemon=True)
thread0.start()

thread1 = Thread(target=read_sensors, args=(event_read,), daemon=True)
thread1.start()

# Initialize the app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap"
    ],
)

app.layout = html.Div(
    [
        html.H1(
            "Mattnetometer System",
            style={
                "padding-left": "20px",
                "border-bottom": "1px solid black",
                "padding-bottom": "5px",
                "color": "#1F3342",
                "font-family": "Roboto",
                "font-size": "38px",
            },
        ),
        html.Div(
            [
                html.Label(
                    "Select Sensors:",
                    style={
                        "font-size": "35px",
                        "margin-left": "10px",
                        "margin-right": "10px",
                    },
                ),
                dcc.Checklist(
                    id="checkboxes",
                    options=[{"label": f"{i+1}", "value": f"{i+1}"} for i in range(12)],
                    value=["1"],  # Default selection
                    inline=True,
                    labelStyle={"padding-right": "10px"},
                ),
            ],
            style={
                "display": "flex",
                "margin-left": "15px",
                "align-items": "center",
            },
            className="checkboxes",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "Grid Layout:",
                            style={
                                "marginRight": "5px",
                                "font-size": "18px",
                                "margin-left": "10px",
                                "display": "inline",
                            },
                        ),
                        dcc.Input(
                            id="grid-rows",
                            type="number",
                            min=1,
                            value=1,
                            style={"width": "30px", "display": "inline"},
                        ),
                        html.Label(
                            "x",
                            style={
                                "marginLeft": "5px",
                                "marginRight": "5px",
                                "display": "inline",
                            },
                        ),
                        dcc.Input(
                            id="grid-cols",
                            type="number",
                            min=1,
                            value=1,
                            style={
                                "marginRight": "10px",
                                "width": "30px",
                                "display": "inline",
                            },
                        ),
                        html.Label(
                            "Layout Mode:",
                            style={
                                "margin-right": "1px",
                                "margin-left": "5px",
                                "display": "inline",
                            },
                        ),
                        dcc.RadioItems(
                            id="layout-toggle",
                            options=[
                                {"label": "Fit to Window", "value": "fit"},
                                {"label": "Scrolling Layout", "value": "scroll"},
                            ],
                            value="fit",
                            inline=True,
                            style={"display": "inline"},
                        ),
                    ]
                ),
            ],
            style={"margin-top": "10px", "margin-left": "15px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "Graph Width in Scrolling Layout:",
                            style={"margin-left": "25px", "font-size": "18px"},
                        ),
                        html.Div(
                            [
                                dcc.Slider(
                                    id="graph-width-slider",
                                    min=25,
                                    max=100,
                                    step=1,
                                    value=25,  # Default graph size
                                    # marks={300: "300px", 600: "600px", 900: "900px"},
                                    marks=None,
                                    disabled=True,
                                )
                            ],
                            style={"marginTop": "5px"},
                        ),
                    ],
                    style={
                        "marginTop": "10px",
                        "display": "inline-block",
                        "width": "48vw",
                    },
                ),
                html.Div(
                    [
                        html.Label(
                            "Graph Height in Scrolling Layout:",
                            style={"margin-left": "25px", "font-size": "18px"},
                        ),
                        html.Div(
                            [
                                dcc.Slider(
                                    id="graph-height-slider",
                                    min=25,
                                    max=100,
                                    step=1,
                                    value=25,  # Default graph size
                                    # marks={300: "300px", 600: "600px", 900: "900px"},
                                    marks=None,
                                    disabled=True,
                                )
                            ],
                            style={"marginTop": "5px"},
                        ),
                    ],
                    style={
                        "marginTop": "10px",
                        "display": "inline-block",
                        "width": "48vw",
                    },
                ),
            ],
            style={"justify-content": "space-between", "display": "flex"},
        ),
        html.Div(
            id="graphs-container",
            style={
                "display": "grid",
                "gap": "10px",
                "width": "100%",
                "height": "80%",  # Subtract header height
                "padding": "10px",
                "boxSizing": "border-box",
            },
        ),
        dcc.Interval(
            id="interval-component",
            interval=1000,  # Update every 1 second
            n_intervals=0,
        ),
    ],
    style={"color": "#003049"},
)


@app.callback(
    Output("graphs-container", "children"),
    Output("graphs-container", "style"),
    Output("graph-width-slider", "disabled"),
    Output("graph-height-slider", "disabled"),
    [
        Input("checkboxes", "value"),
        Input("layout-toggle", "value"),
        Input("graph-width-slider", "value"),
        Input("graph-height-slider", "value"),
        Input("interval-component", "n_intervals"),
    ],
    [State("grid-rows", "value"), State("grid-cols", "value")],
    prevent_initial_call=True,
)
def update_graphs(
    selected_sensors,
    layout_mode,
    graph_width_value,
    graph_height_value,
    n_intervals,
    rows,
    cols,
):

    # Ensure graphs are always displayed in numerical order
    sorted_series = sorted(selected_sensors, key=lambda x: int(x))
    sliderOff = True

    # Dynamically calculate the size for each graph if "fit" mode is selected
    if layout_mode == "fit":
        gap = 20  # Gap between grid items
        padding = 20  # Total padding of the container (10px on each side)
        available_width = f"calc(100vw - {padding}px - {gap * (cols - 1)}px)"
        available_height = f"calc(100vh - 150px - {padding}px - {gap * (rows - 1)}px)"
        graph_width = f"calc({available_width} / {cols})"
        graph_height = f"calc({available_height} / {rows})"
    else:  # Use the slider value for graph size in "scroll" mode
        # graph_width = f"{graph_width_value}px"
        graph_width = f"{graph_width_value}vw"
        # graph_height = f"{graph_height_value}px"
        graph_height = f"{graph_height_value}vh"
        sliderOff = False

    # Generate a graph for each selected series
    graphs = []
    times = Series(timestamps, dtype=object)
    for sensor in sorted_series:
        graphs.append(
            html.Div(
                [
                    dcc.Graph(
                        id=f"graph-{sensor}",
                        figure={
                            "data": [
                                go.Scatter(
                                    x=list(times),
                                    y=list(readings[int(sensor) - 1]),
                                    mode="lines",
                                    name=sensor,
                                    line={"color": "#352F44"},
                                )
                            ],
                            "layout": go.Layout(
                                title=f"Sensor {sensor}",
                                xaxis={
                                    "gridcolor": "black",
                                    "zerolinecolor": "black",
                                    "tickformat": "%H:%M:%S",
                                },
                                yaxis=dict(gridcolor="black", zerolinecolor="black"),
                                plot_bgcolor="#fdf0d5",
                                paper_bgcolor="#fdf0d5",
                                margin={
                                    "l": 10,
                                    "r": 10,
                                    "t": 30,
                                    "b": 25,
                                },  # Minimize margins for compact fit
                            ),
                        },
                        style={"width": "100%", "height": "100%"},
                    )
                ],
                style={
                    "width": graph_width,
                    "height": graph_height,
                },
            )
        )

    # Update grid style based on layout mode
    if layout_mode == "fit":
        grid_style = {
            "display": "grid",
            "gridTemplateRows": f"repeat({rows}, 1fr)",
            "gridTemplateColumns": f"repeat({cols}, 1fr)",
            # 'gap': '10px',
            "grid-gap": "10px",
            "width": "100%",
            "height": "100%",  # Adjust for header height
            "margin-right": "10px",
            "boxSizing": "border-box",
            "overflow": "hidden",  # Prevent scrollbars
        }
    else:  # Scrolling layout
        grid_style = {
            "display": "grid",
            "gridTemplateRows": f"repeat({rows}, auto)",
            "gridTemplateColumns": f"repeat({cols}, auto)",
            # 'gap': '10px',
            "grid-gap": "10px",
            "width": "100%",
            "height": "100%",
            "boxSizing": "border-box",
            "overflow": "auto",  # Enable scrollbars
        }

    return graphs, grid_style, sliderOff, sliderOff


if __name__ == "__main__":
    app.run_server("0.0.0.0", debug=True)
