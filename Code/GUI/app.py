import dash
from dash import dcc, html, ctx
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from numpy import linspace, nanmin, nanmax
from datetime import datetime
from serial import Serial
from collections import deque
from time import sleep
from pandas import Series
from threading import Thread, Event
from os import makedirs, path

ser = Serial(baudrate=115200, timeout=1)
readings = [deque(maxlen=36000) for _ in range(12)]
timestamps = deque(maxlen=36000)
connected = False
log_path = ""

def write_data(base_path):

    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%B")
    week = f"Week-{now.strftime('%U')}"
    day = f"Day-{now.strftime('%d')}.txt"

    # Make month path
    month_folder_path = path.join(base_path, year, month)

    # Check if month folder exists
    if not path.exists(month_folder_path):
        makedirs(month_folder_path)

    # Make week path
    week_folder_path = path.join(month_folder_path, week)

    # Check if week folder exists
    if not path.exists(week_folder_path):
        makedirs(week_folder_path)

    # Make the full path
    day_file_path = path.join(week_folder_path, day)
    file_exists = path.exists(day_file_path)

    # Open the file for appending
    with open(day_file_path, "a") as file:
        if not file_exists:
            # Write a header if the file is new
            file.write(
                "# Magnetic field log file for {}/{}/{}, created at {}:{}:{}. Field values are in uT.\n".format(
                    now.strftime("%Y"),
                    now.strftime("%m"),
                    now.strftime("%d"),
                    now.strftime("%H"),
                    now.strftime("%M"),
                    now.strftime("%S"),
                )
            )
        file.write(
            "{}:{}:{}:{}\t".format(
                timestamps[-1].strftime("%H"),
                timestamps[-1].strftime("%M"),
                timestamps[-1].strftime("%S"),
                timestamps[-1].strftime("%f"),
            )
        )
        for i in range(12):
            if i != 11:
                file.write("{:.6f}\t".format(readings[i][-1]))
            else:
                file.write("{:.6f}\n".format(readings[i][-1]))

    return day_file_path


def server_tick(event_a):
    """This function is used to generate the 1s interval to sample the instruments. Doing it
        it in the background of the server prevents possible collisions if there is more than one
        client viewing the dashboard. It also allows the instruments to still be read and logged
        even when no clients are connected.

    Args:
        event (Event): Triggers arduino to read sensors
    """

    while True:

        sleep(1)  # Sets the sample rate to 1 second
        timestamps.append(datetime.now())
        event_a.set()
        print("tick", datetime.now().strftime("%H:%M:%S:%f"))


def read_sensors(event_read, event_connected, event_log):
    global log_path
    while True:
        event_read.wait()

        if event_connected.is_set():
            ser.write(b"R")
            values = ser.readline().decode().strip().split()
            # values = np.random.uniform(0, 1, 12)
            for i in range(12):
                if values[i] == "999.00000000":
                    readings[i].append(float("nan"))
                else:
                    readings[i].append(float(values[i]))

            if event_log.is_set():
                write_data(log_path)

        event_read.clear()


event_read = Event()
event_connected = Event()
event_log = Event()

thread0 = Thread(
    target=server_tick,
    args=(event_read,),
    daemon=True,
)
thread0.start()

thread1 = Thread(
    target=read_sensors,
    args=(
        event_read,
        event_connected,
        event_log,
    ),
    daemon=True,
)
thread1.start()

# Initialize the app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap",
    ],
)

app.layout = html.Div(
    [
        html.Div(
            "Magnetometer System",
            style={
                "padding-left": "25px",
                "border-bottom": "1px solid black",
                "padding-bottom": "5px",
                "font-size": "75px",
                "margin-top": "10px",
                "font-family": "VT323",
                "margin-bottom": "10px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "PORT:",
                            style={"font-size": "25px", "margin-right": "10px"},
                        ),
                        dcc.Input(
                            id="port",
                            type="text",
                            size="5",
                            style={
                                "margin-right": "15px",
                                "font-size": "20px",
                                "font-family": "Share Tech Mono",
                            },
                        ),
                        html.Button(
                            "Connect",
                            id="connect-button",
                            className="hp-button",
                            style={"margin-right": "10px", "width": "150px"},
                        ),
                    ],
                    style={
                        "border-right": "1px solid black",
                        "align-items": "center",
                        "display": "flex",
                    },
                ),
                html.Div(
                    [
                        html.Label(
                            "Log Directory:",
                            style={
                                "font-size": "25px",
                                "margin-right": "10px",
                                "margin-left": "10px",
                            },
                        ),
                        dcc.Input(
                            id="log-path",
                            type="text",
                            size="25",
                            autoComplete="off",
                            style={
                                "margin-right": "15px",
                                "font-size": "20px",
                                "font-family": "Share Tech Mono",
                            },
                        ),
                        html.Button(
                            "Start",
                            id="log-button",
                            className="hp-button",
                            style={"margin-right": "10px"},
                        ),
                    ],
                    style={"align-items": "center", "display": "flex"},
                ),
            ],
            style={
                "margin-left": "25px",
                "margin-bottom": "5px",
                "display": "flex",
                "align-items": "center",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "Grid Layout:",
                            style={
                                "marginRight": "5px",
                                "font-size": "25px",
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
                    ],
                    style={
                        "border-right": "1px solid #333333",
                        "display": "flex",
                        "align-items": "center",
                    },
                ),
                html.Div(
                    [
                        html.Label(
                            "Plot Size:",
                            style={
                                "margin-right": "1px",
                                "margin-left": "15px",
                                "display": "inline",
                                "font-size": "25px",
                            },
                        ),
                        dcc.RadioItems(
                            id="layout-toggle",
                            options=[
                                {"label": "Fit", "value": "fit"},
                                {"label": "Custom", "value": "scroll"},
                            ],
                            value="fit",
                            inline=True,
                            style={"display": "inline"},
                            labelStyle={"padding-right": "10px", "font-size": "25px"},
                            className="radio",
                        ),
                    ],
                    style={
                        "border-right": "1px solid #333333",
                        "display": "flex",
                        "align-items": "center",
                    },
                ),
                html.Label(
                    "Plot Style:",
                    style={
                        "margin-right": "1px",
                        "margin-left": "15px",
                        "display": "inline",
                        "font-size": "25px",
                    },
                ),
                dcc.RadioItems(
                    id="style-toggle",
                    options=[
                        {"label": "Light", "value": "light"},
                        {"label": "Dark", "value": "dark"},
                    ],
                    value="light",
                    inline=True,
                    style={"display": "inline"},
                    labelStyle={"padding-right": "10px", "font-size": "25px"},
                    className="radio",
                ),
            ],
            style={
                "margin-left": "15px",
                "display": "flex",
                "align-items": "center",
                "margin-bottom": "10px",
            },
        ),
        html.Div(
            [
                html.Label(
                    "Select Sensors:",
                    style={
                        "font-size": "25px",
                        "margin-left": "10px",
                        "margin-right": "10px",
                    },
                ),
                dcc.Checklist(
                    id="checkboxes",
                    options=[{"label": f"{i+1}", "value": f"{i+1}"} for i in range(12)],
                    inline=True,
                    labelStyle={"padding-right": "10px", "font-size": "18px"},
                    className="checkboxes",
                ),
            ],
            style={
                "display": "flex",
                "margin-left": "15px",
                "align-items": "center",
                "margin-bottom": "5px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            "Graph Width:",
                            style={"margin-left": "25px", "font-size": "18px"},
                        ),
                        html.Div(
                            [
                                dcc.Slider(
                                    id="graph-width-slider",
                                    min=10,
                                    max=100,
                                    step=1,
                                    value=25,  # Default graph size
                                    # marks={300: "300px", 600: "600px", 900: "900px"},
                                    marks=None,
                                )
                            ],
                            style={"marginTop": "5px"},
                        ),
                    ],
                    style={
                        "display": "inline-block",
                        "width": "48vw",
                    },
                ),
                html.Div(
                    [
                        html.Label(
                            "Graph Height:",
                            style={"margin-left": "25px", "font-size": "18px"},
                        ),
                        html.Div(
                            [
                                dcc.Slider(
                                    id="graph-height-slider",
                                    min=10,
                                    max=100,
                                    step=1,
                                    value=25,  # Default graph size
                                    # marks={300: "300px", 600: "600px", 900: "900px"},
                                    marks=None,
                                )
                            ],
                            style={"marginTop": "5px"},
                        ),
                    ],
                    style={
                        "display": "inline-block",
                        "width": "48vw",
                    },
                ),
            ],
            id="slider-container",
            style={"justify-content": "space-between", "display": "none"},
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
        dcc.Interval(
            id="button-reset",
            interval=3000,  # Update every 1 second
            n_intervals=0,
            disabled=True,
        ),
    ],
    style={"color": "#003049"},
)


@app.callback(
    Output("graphs-container", "children"),
    Output("graphs-container", "style"),
    Output("slider-container", "style"),
    Input("checkboxes", "value"),
    Input("layout-toggle", "value"),
    Input("graph-width-slider", "value"),
    Input("graph-height-slider", "value"),
    Input("interval-component", "n_intervals"),
    State("grid-rows", "value"),
    State("grid-cols", "value"),
    State("style-toggle", "value"),
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
    plot_style,
):
    if layout_mode == "fit":
        grid_style = {
            "display": "grid",
            "gridTemplateRows": f"repeat({rows}, 1fr)",
            "gridTemplateColumns": f"repeat({cols}, 1fr)",
            "grid-gap": "5px",
            "boxSizing": "border-box",
            "overflow": "hidden",  # Prevent scrollbars
            "margin": "auto",
        }
        style = {"justify-content": "space-between", "display": "None"}
    else:  # Scrolling layout
        grid_style = {
            "display": "grid",
            "gridTemplateRows": f"repeat({rows}, auto)",
            "gridTemplateColumns": f"repeat({cols}, auto)",
            "grid-gap": "5px",
            "boxSizing": "border-box",
            "overflow": "auto",  # Enable scrollbars
            "margin": "auto",
        }
        style = {
            "justify-content": "space-between",
            "display": "flex",
            "margin-bottom": "5px",
        }

    if selected_sensors is not None and event_connected.is_set():

        sorted_series = sorted(selected_sensors, key=lambda x: int(x))

        # Dynamically calculate the size for each graph if "fit" mode is selected
        if layout_mode == "fit":
            gap = 5  
            padding = 60  
            available_width = f"calc(95vw - {gap * (cols - 1)}px)"
            available_height = (
                f"calc(100vh - 175px - {padding}px - {gap * (rows - 1)}px)"
            )
            graph_width = f"calc({available_width} / {cols})"
            graph_height = f"calc({available_height} / {rows})"

        else:  # Use the slider value for graph size in "scroll" mode
            # graph_width = f"{graph_width_value}px"
            graph_width = f"{graph_width_value}vw"
            # graph_height = f"{graph_height_value}px"
            graph_height = f"{graph_height_value}vh"
            sliderOff = False
            style = {"justify-content": "space-between", "display": "flex"}

        # grid_color = "#2f4f4f"
        if plot_style == "light":
            trace_color = "#3b5c8f"
            grid_color = "#2f4f4f"
            background_color = "#f5f5f5"
            font_color = "#333333"
        else:
            trace_color = "#0FFF50"
            grid_color = "#c2c2c2"
            background_color = "#1a1a1a"
            font_color = "#cfcfcf"

        # Generate a graph for each selected series
        graphs = []
        times = Series(timestamps, dtype=object)
        for sensor in sorted_series:
            num_ticks = 10
            ticks = linspace(
                # min(readings[int(sensor) - 1], default=0),
                # max(readings[int(sensor) - 1], default=0),
                nanmin(readings[int(sensor) - 1]),
                nanmax(readings[int(sensor) - 1]),
                num_ticks,
            )
            tick_labels = [f"{tick:.6g}" for tick in ticks]
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
                                        line={"color": trace_color},
                                    )
                                ],
                                "layout": go.Layout(
                                    title={
                                        "text": f"Sensor {sensor} = {readings[int(sensor) - 1][-1]:.5f} uT",
                                        "font": {
                                            "color": font_color,
                                            "family": "Share Tech Mono",
                                        },
                                    },
                                    xaxis={
                                        "showline": True,
                                        "linewidth": 2,
                                        "linecolor": font_color,
                                        "mirror": True,
                                        "gridcolor": grid_color,
                                        "zeroline": False,
                                        "tickformat": "%H:%M:%S",
                                        "tickfont": {"color": font_color},
                                    },
                                    yaxis={
                                        "title": dict(text="B (uT)"),
                                        "showline": True,
                                        "linewidth": 2,
                                        "linecolor": font_color,
                                        "mirror": True,
                                        "gridcolor": grid_color,
                                        "zeroline": False,
                                        "tickfont": {"color": font_color},
                                        "tickvals": ticks.tolist(),
                                        "ticktext": tick_labels,
                                    },
                                    plot_bgcolor=background_color,
                                    paper_bgcolor=background_color,
                                    margin={
                                        "l": 75,
                                        "r": 10,
                                        "t": 45,
                                        "b": 25,
                                    },
                                ),
                            },
                            style={"height": "100%", "width": "100%"},
                        )
                    ],
                    style={
                        "width": graph_width,
                        "height": graph_height,
                        "display": "flex",
                        "justify-self": "center",
                        "align-self": "center"
                    },
                )
            )

        return graphs, grid_style, style

    else:
        return [], {}, style


@app.callback(
    Output("connect-button", "className"),
    Output("connect-button", "children"),
    Output("button-reset", "disabled"),
    Output("button-reset", "n_intervals"),
    Input("connect-button", "n_clicks"),
    Input("button-reset", "n_intervals"),
    State("port", "value"),
    State("connect-button", "className"),
    prevent_initial_call=True,
)
def connect_arduino(n_clicks, n_intervals, port, current_class):

    triggered_id = ctx.triggered_id

    if (
        triggered_id == "connect-button"
        and port != None
        and event_connected.is_set() != 1
    ):

        try:
            ser.port = port
            ser.open()
        except:
            print("failed to open serial port")

        else:
            print("connecting")

        return "hp-button-loading", "Connecting", False, 0

    elif triggered_id == "connect-button" and event_connected.is_set():
        ser.close()
        event_connected.clear()

        return "hp-button", "Connect", True, 0

    if triggered_id == "button-reset":
        if ser.is_open:
            ser.write(b"I")
            out = ser.readline().decode().strip()
            if out == "Magnetometer Controller":
                event_connected.set()
                return "hp-button-success", "Connected", True, 0
            else:
                return "hp-button-fail", "Failed", True, 0
        else:
            return "hp-button-fail", "Failed", True, 0

    return dash.no_update, "Connect", True, 0


@app.callback(
    Output("log-button", "className"),
    Output("log-button", "children"),
    Input("log-button", "n_clicks"),
    State("log-path", "value"),
    prevent_initial_call=True,
)
def start_log(n, user_path):
    global log_path, event_log

    if path.exists(user_path):

        log_path = user_path

        if event_log.is_set():

            event_log.clear()

            return "hp-button", "Start"

        else:

            event_log.set()

            return "hp-button-success", "Logging"

    else:
        print("Bad path")
        return "hp-button-fail", "Bad Path"


if __name__ == "__main__":
    app.run(debug=False)
