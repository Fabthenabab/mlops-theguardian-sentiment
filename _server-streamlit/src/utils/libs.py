import pandas as pd
import plotly.graph_objects as go

def plot_forecast(df: pd.DataFrame, title: str):
    fig = go.Figure()

    # Trust interval
    fig.add_trace(go.Scatter(
        x=pd.concat([df["ds"], df["ds"][::-1]]),
        y=pd.concat([df["yhat_upper"], df["yhat_lower"][::-1]]),
        fill="toself",
        fillcolor="rgba(0, 100, 255, 0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Confidence interval"
    ))

    # Graphic yhat
    fig.add_trace(go.Scatter(
        x=df["ds"], y=df["yhat"],
        line=dict(color="royalblue", width=2),
        name="Forecast"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Sentiment score",
        hovermode="x unified"
    )
    return fig