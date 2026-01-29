import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

st.title("COVID-19 Data Visualization Dashboard")
st.markdown("""
This dashboard explores global COVID-19 trends, vaccination progress,
and their relationship with deaths across countries.
""")

@st.cache_data(ttl=24 * 60 * 60)  # cache for 24 hours
def load_data():
    urls = [
        "https://covid.ourworldindata.org/data/owid-covid-data.csv",
        "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv",
    ]
    last_error = None
    for url in urls:
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Failed to download dataset. Last error: {last_error}")

df = load_data()

# Sidebar filters
countries = sorted(df["location"].dropna().unique())
default_index = countries.index("India") if "India" in countries else 0

selected_country = st.sidebar.selectbox(
    "Select a Country",
    countries,
    index=default_index
)

min_date = df["date"].min().date()
max_date = df["date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Ensure date_range always has 2 values
start_date, end_date = date_range if isinstance(date_range, tuple) else (date_range, date_range)

filtered_df = df[
    (df["location"] == selected_country) &
    (df["date"].dt.date >= start_date) &
    (df["date"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("No data available for the selected filters. Try a different date range.")
    st.stop()

latest = filtered_df.sort_values("date").iloc[-1]

# KPI metrics (handle missing values safely)
col1, col2, col3 = st.columns(3)

total_cases = latest.get("total_cases")
total_deaths = latest.get("total_deaths")
fully_vax = latest.get("people_fully_vaccinated_per_hundred")

col1.metric("Total Cases", f"{int(total_cases):,}" if pd.notna(total_cases) else "N/A")
col2.metric("Total Deaths", f"{int(total_deaths):,}" if pd.notna(total_deaths) else "N/A")
col3.metric("Fully Vaccinated (%)", f"{fully_vax:.1f}" if pd.notna(fully_vax) else "N/A")

# Chart 1: Area chart for total cases over time
fig = px.area(
    filtered_df,
    x="date",
    y="total_cases",
    title=f"Total COVID-19 Cases Over Time — {selected_country}"
)
st.plotly_chart(fig, use_container_width=True)

# Latest snapshot per country for cross-country charts
latest_all = df.sort_values("date").groupby("location").last().reset_index()

# Chart 2: Top 10 by deaths per million (remove non-countries)
top10 = latest_all.dropna(subset=["total_deaths_per_million"])
top10 = top10[top10["location"] != "World"].sort_values("total_deaths_per_million", ascending=False).head(10)

fig2 = px.bar(
    top10,
    x="location",
    y="total_deaths_per_million",
    title="Top 10 Countries by Deaths per Million"
)
st.plotly_chart(fig2, use_container_width=True)

# Chart 3: Scatter vaccination vs deaths per million
scatter_df = latest_all[
    ["people_fully_vaccinated_per_hundred", "total_deaths_per_million", "location"]
].dropna()

scatter_df = scatter_df[scatter_df["location"] != "World"]

fig3 = px.scatter(
    scatter_df,
    x="people_fully_vaccinated_per_hundred",
    y="total_deaths_per_million",
    hover_name="location",
    title="Vaccination Rate vs Deaths per Million"
)
st.plotly_chart(fig3, use_container_width=True)

# Data preview
st.subheader("Filtered Data Preview")
st.dataframe(filtered_df.head(50))
