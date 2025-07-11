import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from io import BytesIO
import base64
import json

st.set_page_config(page_title="Stock Market Visualizer", layout="wide")
st.title("📈 Stock Market Visualizer")

# Sidebar configuration
st.sidebar.header("📊 Configuration")

# Ticker input
ticker = st.sidebar.text_input("Stock Ticker:", "AAPL").upper()

# Date range input
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2020-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp.today())

# Indicators
with st.sidebar.expander("Overlay Indicators"):
    use_ma = st.checkbox("Moving Averages (20, 50)", value=True)
    use_rsi = st.checkbox("RSI (14)", value=False)
    use_bb = st.checkbox("Bollinger Bands (20, 2σ)", value=False)

# Chart options
with st.sidebar.expander("Chart Settings"):
    timeframe = st.selectbox("Chart Timeframe:", ["Daily", "Weekly", "Monthly"])
    color_up = st.color_picker("Candle ↑ Color", "#00B050")
    color_down = st.color_picker("Candle ↓ Color", "#FF0000")

# Portfolio upload
portfolio_file = st.sidebar.file_uploader("Upload Portfolio (CSV/XLSX)", type=["csv", "xlsx"])

# Configuration save/load
if "config" not in st.session_state:
    st.session_state.config = {}

if st.sidebar.button("Save Configuration"):
    st.session_state.config = {
        "ticker": ticker,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "use_ma": use_ma,
        "use_rsi": use_rsi,
        "use_bb": use_bb,
        "timeframe": timeframe,
        "color_up": color_up,
        "color_down": color_down,
    }
    st.sidebar.success("✅ Configuration saved.")

if st.sidebar.button("Load Configuration") and st.session_state.config:
    cfg = st.session_state.config
    ticker = st.sidebar.text_input("Stock Ticker:", cfg["ticker"])
    start_date = st.sidebar.date_input("Start Date", pd.to_datetime(cfg["start_date"]))
    end_date = st.sidebar.date_input("End Date", pd.to_datetime(cfg["end_date"]))
    use_ma = st.sidebar.checkbox("Moving Averages (20, 50)", cfg["use_ma"])
    use_rsi = st.sidebar.checkbox("RSI (14)", cfg["use_rsi"])
    use_bb = st.sidebar.checkbox("Bollinger Bands (20, 2σ)", cfg["use_bb"])
    timeframe = st.selectbox("Chart Timeframe:", ["Daily", "Weekly", "Monthly"], index=["Daily", "Weekly", "Monthly"].index(cfg["timeframe"]))
    color_up = st.color_picker("Candle ↑ Color", cfg["color_up"])
    color_down = st.color_picker("Candle ↓ Color", cfg["color_down"])
    st.sidebar.success("🔄 Configuration loaded.")

@st.cache_data
def load_data(ticker, start, end):
    return (yf.download(ticker, start=start, end=end, auto_adjust=True)
            .assign(RSI=lambda x: compute_rsi(x['Close']))
            .assign(MA20=lambda x: x['Close'].rolling(20).mean(),
                    MA50=lambda x: x['Close'].rolling(50).mean())
            .pipe(add_bollinger)
           )

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = -delta.clip(upper=0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_bollinger(df):
    ma = df['Close'].rolling(20).mean()
    sd = df['Close'].rolling(20).std()
    df['BB_up'] = ma + 2 * sd
    df['BB_dn'] = ma - 2 * sd
    return df

# Fetch data
df = load_data(ticker, start_date, end_date)

if df.empty:
    st.error("⚠️ No data available.")
    st.stop()

# Resampling
if timeframe == "Weekly":
    df = df.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum','RSI':'last','MA20':'last','MA50':'last','BB_up':'last','BB_dn':'last'})
elif timeframe == "Monthly":
    df = df.resample('M').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum','RSI':'last','MA20':'last','MA50':'last','BB_up':'last','BB_dn':'last'})

df.reset_index(inplace=True)

# Plot candlestick chart
fig = go.Figure(data=[go.Candlestick(x=df['Date'],
                                     open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color=color_up, decreasing_line_color=color_down)])
if use_ma:
    fig.add_traces([
        go.Scatter(x=df['Date'], y=df['MA20'], name="MA20", line=dict(color="blue")),
        go.Scatter(x=df['Date'], y=df['MA50'], name="MA50", line=dict(color="orange"))
    ])
if use_bb:
    fig.add_traces([
        go.Scatter(x=df['Date'], y=df['BB_up'], name="BB Upper", line=dict(color="green", dash="dash")),
        go.Scatter(x=df['Date'], y=df['BB_dn'], name="BB Lower", line=dict(color="red", dash="dash"))
    ])
fig.update_layout(title=f"{ticker} Candlestick Chart", xaxis_title="Date", yaxis_title="Price", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# RSI subplot
if use_rsi:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], name="RSI"))
    fig2.update_layout(title="RSI (14)", yaxis=dict(range=[0,100]), xaxis_title="Date")
    st.plotly_chart(fig2, use_container_width=True)

# Portfolio tracking
if portfolio_file:
    st.subheader("📁 Portfolio Analysis")
    pf = pd.read_csv(portfolio_file) if portfolio_file.name.endswith('.csv') else pd.read_excel(portfolio_file)
    st.dataframe(pf)
    symbols = pf['Ticker'].tolist()
    prices = {sym: yf.Ticker(sym).history(period="1d")['Close'].iloc[-1] for sym in symbols}
    pf['Current Value'] = pf['Shares'] * pf['Ticker'].map(prices)
    st.bar_chart(pf.set_index('Ticker')['Current Value'])

    # Correlation
    data2 = pd.concat([yf.download(sym, start=start_date, end=end_date)['Close'] for sym in symbols], axis=1)
    data2.columns = symbols
    corr = data2.pct_change().corr()
    st.subheader("📈 Correlation Matrix")
    st.dataframe(corr)

# Export buttons
buf_png = fig.to_image(format="png")
href = f'<a href="data:image/png;base64,{base64.b64encode(buf_png).decode()}" download="{ticker}_chart.png">📥 Download PNG</a>'
st.markdown(href, unsafe_allow_html=True)

buf_html = fig.to_html(full_html=False)
href2 = f'<a href="data:text/html;base64,{base64.b64encode(buf_html.encode()).decode()}" download="{ticker}_chart.html">📥 Download HTML</a>'
st.markdown(href2, unsafe_allow_html=True)

