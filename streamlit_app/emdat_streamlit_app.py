import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient


def main():
    mongo_url = st.secrets["MONGO_URI"]

    df = load_data(mongo_url)
    st.set_page_config(page_title="EM-DAT Disaster Data Dashboard")
    sidebar(df)


# Connect to MongoDB
def load_data(mongo_url):
    client = MongoClient(mongo_url)  # Replace with your MongoDB connection string
    db = client["test_db"]  # Replace with your database name
    collection = db["emdat_test1"]  # Replace with your collection name

    # Load data and count occurrences manually
    fetch_data = list(collection.find())

    # Make data frame
    df = pd.json_normalize(fetch_data)
    return df


# Navigation Side Bar
def sidebar(df):
    st.sidebar.title("Navigation")
    tab = st.sidebar.radio("Go to", ["📊 Disaster Data", "💥 Disaster Impact", "🗺️ Country-Wise Disaster Info"])

    if tab == "📊 Disaster Data":
        st.title("📊 EM-DAT Disaster Data")
        st.write("Data of this site were from [EM-DAT The International Disaster Database](https://www.emdat.be/). "
                 "Disaster data were being visualized to provide more understanding about disasters to the public.")
        show_df_table(df)
        pie_chart_disaster_type(df)
        line_graph_disaster_trend(df)

    elif tab == "💥 Disaster Impact":
        st.title("💥 Disaster Impact")
        st.write("Different types of disaster causes different impacts. Graph below shows which disaster had caused "
                 "fatality accumulated from 1900 - then.\n\n")
        bar_chart_disaster_vs_impact(df)
        disaster_impact_comparison_table(df)

    elif tab == "🗺️ Country-Wise Disaster Info":
        st.title("🗺️ Country-Wise Disaster Info")
        country_wise_data_page(df)
        pie_chart_disaster_type_by_country(df)
        world_map_of_disasters(df)


def show_df_table(df):
    st.dataframe(df)


def pie_chart_disaster_type(df):
    st.header("\n🥧 Disaster Type Distribution")

    disaster_counts = df["disaster_info.disaster_type"].value_counts()

    top_10 = disaster_counts.nlargest(10)
    others_count = disaster_counts.iloc[10:].sum()

    disaster_labels = list(top_10.index) + (["Others"] if others_count > 0 else [])
    disaster_sizes = list(top_10.values) + ([others_count] if others_count > 0 else [])

    fig, ax = plt.subplots()
    ax.pie(
        disaster_sizes,
        labels=disaster_labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=None
    )
    ax.axis("equal")

    st.pyplot(fig)


def line_graph_disaster_trend(df):
    st.header("📈 Disaster Trend Line Graph")
    df["timeline.start_year"] = pd.to_numeric(df["timeline.start_year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["timeline.start_year"])
    df["timeline.start_year"] = df["timeline.start_year"].astype(int)

    df = df.sort_values("timeline.start_year")

    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        start_year = st.selectbox("Select Start Year", sorted(df["timeline.start_year"].unique()), index=0)
    with col2:
        unique_years = sorted(df["timeline.start_year"].unique())

        # Ensure there's at least one option
        if len(unique_years) > 0:
            end_year = st.selectbox("Select End Year", unique_years, index=len(unique_years) - 1)
        else:
            end_year = None  # Handle empty case
    with col3:
        disaster_type = st.selectbox("Select Disaster Type", sorted(df["disaster_info.disaster_type"].unique()))

    df_filtered = df[
        (df["timeline.start_year"] >= start_year) &
        (df["timeline.start_year"] <= end_year) &
        (df["disaster_info.disaster_type"] == disaster_type)
        ]

    df_trend = df_filtered.groupby("timeline.start_year").size().reset_index(name="count")

    if df_trend.empty:
        st.write("⚠️ No Records found.")
    else:
        fig, ax = plt.subplots()
        ax.plot(df_trend["timeline.start_year"], df_trend["count"], marker="o", linestyle="-", color="b")
        ax.set_title(f"Trend of {disaster_type} from {start_year} to {end_year}")
        ax.set_xlabel("Year")
        ax.set_ylabel("Number of Disasters")
        ax.grid(True)

        st.pyplot(fig)


def disaster_impact_comparison_table(df):
    st.header("⚖️ Disaster Average Impact Comparison")

    disaster_types = sorted(df["disaster_info.disaster_type"].dropna().unique())

    if len(disaster_types) < 2:
        st.warning("Not enough disaster types available for comparison.")
        return

    metrics = [
        "impact_info.total_deaths",
        "financial_info.reconstruction_cost_usd_adjusted",
        "financial_info.insured_damage_usd_adjusted",
        "financial_info.total_damage_usd_adjusted",
        "impact_info.injured_number",
        "impact_info.affected_number",
        "impact_info.homeless_number",
        "impact_info.total_affected"
    ]

    df[metrics] = df[metrics].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=metrics, how="all")

    col1, col2 = st.columns(2)
    with col1:
        disaster_a = st.selectbox("Select Disaster A", disaster_types, index=0)

    disaster_b_options = [d for d in disaster_types if d != disaster_a]

    with col2:
        if disaster_b_options:
            disaster_b = st.selectbox("Select Disaster B", disaster_b_options, index=0)
        else:
            disaster_b = None

    if not disaster_b:
        st.warning("Please select different disasters for comparison.")
        return

    avg_a = df[df["disaster_info.disaster_type"] == disaster_a][metrics].mean(numeric_only=True)
    avg_b = df[df["disaster_info.disaster_type"] == disaster_b][metrics].mean(numeric_only=True)

    avg_a = avg_a.reindex(metrics).fillna("nan")
    avg_b = avg_b.reindex(metrics).fillna("nan")

    comparison_data = {
        disaster_a: avg_a.values,
        "Average Impact": [
            "Total Deaths", "Reconstruction Cost (USD Adjusted)", "Insured Damage (USD Adjusted)",
            "Total Damage (USD Adjusted)", "Injured Number", "Affected Number",
            "Homeless Number", "Total Affected"
        ],
        disaster_b: avg_b.values
    }

    comparison_df = pd.DataFrame(comparison_data)

    st.table(comparison_df)


def country_wise_data_page(df):
    country_list = df["location_info.country"].dropna().unique().tolist()
    country_list = [c for c in country_list if c.strip()]  # Remove empty strings
    country_list.sort()

    country_list.insert(0, "All Countries")
    selected_country = st.selectbox("Select Country:", country_list)

    if selected_country != "All Countries":
        df_filtered = df[df["location_info.country"] == selected_country]
    else:
        df_filtered = df

    st.dataframe(df_filtered)


def bar_chart_disaster_vs_impact(df):
    st.header("☠️ Impact of Different Disaster")

    impact_metrics = {
        "Total Deaths": "impact_info.total_deaths",
        "Injured Number": "impact_info.injured_number",
        "Affected Number": "impact_info.affected_number",
        "Homeless Number": "impact_info.homeless_number",
        "Total Affected": "impact_info.total_affected",
        "Reconstruction Cost (USD)": "financial_info.reconstruction_cost_usd_adjusted",
        "Insured Damage (USD)": "financial_info.insured_damage_usd_adjusted",
        "Total Damage (USD)": "financial_info.total_damage_usd_adjusted"
    }

    selected_metric_label = st.selectbox("Select Impact Metric", list(impact_metrics.keys()))
    selected_metric = impact_metrics[selected_metric_label]

    df[selected_metric] = pd.to_numeric(df[selected_metric], errors="coerce")

    df_filtered = df.dropna(subset=[selected_metric])

    df_grouped = df_filtered.groupby("disaster_info.disaster_type")[selected_metric].sum().reset_index()
    df_grouped = df_grouped.sort_values(by=selected_metric, ascending=True)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.barh(df_grouped["disaster_info.disaster_type"], df_grouped[selected_metric], color="red", height=0.5)
    ax.set_title(f"Total {selected_metric_label} by Disaster Type")
    ax.set_xlabel(selected_metric_label)
    ax.set_ylabel("Disaster Type")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(format_k))

    st.pyplot(fig)


def pie_chart_disaster_type_by_country(df):
    st.header("🌍 Disaster Types by Country")

    country_list = sorted(df["location_info.country"].dropna().unique())
    country_list = [c for c in country_list if c.strip()]

    selected_country = st.selectbox("Select a Country", country_list, index=0)

    df_filtered = df[df["location_info.country"] == selected_country]

    if df_filtered.empty:
        st.warning(f"No disaster data available for {selected_country}.")
        return

    disaster_counts = df_filtered["disaster_info.disaster_type"].value_counts()

    top_disasters = disaster_counts[:10]
    others_sum = disaster_counts[10:].sum()

    if others_sum > 0:
        top_disasters = pd.concat([top_disasters, pd.Series({"Others": others_sum})])

    fig, ax = plt.subplots()
    ax.pie(top_disasters, labels=top_disasters.index, autopct="%1.1f%%", colors=plt.cm.Paired.colors)
    ax.set_title(f"Disaster Types in {selected_country}")

    st.pyplot(fig)


def world_map_of_disasters(df):
    st.header("🌍 Disaster Distribution by Country")

    # Ensure ISO codes and disaster types exist
    df["location_info.iso"] = df["location_info.iso"].astype(str)
    df["disaster_info.disaster_type"] = df["disaster_info.disaster_type"].astype(str)

    # Dropdown for disaster type selection
    disaster_type = st.selectbox("Select Disaster Type", sorted(df["disaster_info.disaster_type"].unique()))

    # Filter data based on selection
    df_filtered = df[df["disaster_info.disaster_type"] == disaster_type]

    # Count occurrences per country
    df_map = df_filtered.groupby("location_info.iso").size().reset_index(name="count")

    # Plot world map
    fig = px.choropleth(
        df_map,
        locations="location_info.iso",  # ISO country code
        locationmode="ISO-3",
        color="count",
        hover_name="location_info.iso",
        color_continuous_scale="Reds",
        title=f"Global Distribution of {disaster_type}"
    )

    fig.update_layout(
        height=700,
        width=800,
        coloraxis_colorbar=dict(
            orientation="h",  # Horizontal colorbar
            x=0.5,  # Centered
            y=-0.2,  # Moves below the plot
            xanchor="center",
            title="Number of Disasters"
        )
    )

    st.plotly_chart(fig)


def format_k(x, _):
    return f"{int(x / 1000)}k" if x >= 1000 else str(int(x))


if __name__ == "__main__":
    main()
