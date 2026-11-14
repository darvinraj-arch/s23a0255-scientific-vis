import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="JIE42403 Scientific Visualisation - Malaysia Socioeconomic & Demographic Study",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# DATA LOADING & PREPROCESSING (CACHED)
# ---------------------------------------------------------
@st.cache_data
def load_data():
    df_inc = pd.read_csv("hh_income_parlimen.csv")
    df_exp = pd.read_csv("hh_expenditure_parlimen.csv")
    df_pop = pd.read_csv("population_state_filtered.csv")

    # Extract year from date column
    df_inc["year"] = pd.to_datetime(df_inc["date"]).dt.year
    df_exp["year"] = pd.to_datetime(df_exp["date"]).dt.year
    df_pop["year"] = pd.to_datetime(df_pop["date"]).dt.year

    target_years = sorted(df_inc["year"].unique().tolist())

    # Merge Income and Expenditure at Parliamentary Constituency level (666 rows)
    df_econ = pd.merge(
        df_inc,
        df_exp[["state", "parlimen", "year", "expenditure"]],
        on=["state", "parlimen", "year"],
        how="inner"
    )

    # Derived financial indicators
    df_econ["surplus_mean"] = df_econ["income_mean"] - df_econ["expenditure"]
    df_econ["spending_ratio"] = (df_econ["expenditure"] / df_econ["income_mean"]) * 100
    df_econ["inequality_gap"] = df_econ["income_mean"] - df_econ["income_median"]

    # Map regions
    east_my = ["Sabah", "Sarawak", "W.P. Labuan"]
    fed_terr = ["W.P. Kuala Lumpur", "W.P. Putrajaya", "W.P. Labuan"]

    def get_region(state):
        if state in fed_terr:
            return "Federal Territory"
        elif state in east_my:
            return "East Malaysia"
        return "Peninsular Malaysia"

    df_econ["region"] = df_econ["state"].apply(get_region)

    # Aggregate economic metrics by state & year and merge with Population (48 rows)
    state_econ = (
        df_econ.groupby(["state", "year"])[
            ["income_mean", "income_median", "expenditure", "surplus_mean", "spending_ratio"]
        ]
        .mean()
        .reset_index()
    )
    df_state = pd.merge(
        df_pop[["state", "year", "population"]],
        state_econ,
        on=["state", "year"],
        how="inner"
    )
    df_state["region"] = df_state["state"].apply(get_region)

    return df_econ, df_state, target_years


try:
    df_econ, df_state, years = load_data()
except Exception as e:
    st.error(f"Error loading CSV datasets: {e}")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR NAVIGATION & GLOBAL FILTER
# ---------------------------------------------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Select Visualization Page:",
    [
        "Page 1: Income Inequality & Distribution",
        "Page 2: Household Expenditure & Savings Capacity",
        "Page 3: Population Scale & Regional Dynamics"
    ]
)

st.sidebar.markdown("---")
selected_year = st.sidebar.selectbox("Select Survey Year:", years, index=len(years) - 1)
st.sidebar.caption("Data Source: Department of Statistics Malaysia (OpenDOSM)")

# =========================================================
# PAGE 1: INCOME INEQUALITY & DISTRIBUTION
# =========================================================
if page == "Page 1: Income Inequality & Distribution":
    st.title("Page 1: Intra-State Income Inequality & Distribution")

    # 1. Objective Statement
    st.info(
        "**Objective Statement:** To examine household income distribution and skewness across Malaysian "
        "parliamentary constituencies, highlighting the gap between mean and median earnings."
    )

    df_y = df_econ[df_econ["year"] == selected_year]

    # 2. Summary Box
    st.subheader(f"Summary Box ({selected_year})")
    col1, col2, col3, col4 = st.columns(4)
    avg_mean = df_y["income_mean"].mean()
    avg_med = df_y["income_median"].mean()
    skew_ratio = avg_mean / avg_med
    max_gap_row = df_y.loc[df_y["inequality_gap"].idxmax()]

    col1.metric("National Avg Mean Income", f"RM {avg_mean:,.0f}")
    col2.metric("National Avg Median Income", f"RM {avg_med:,.0f}")
    col3.metric("Mean-to-Median Skew Ratio", f"{skew_ratio:.2f}x", "Right-skewed (>1.0)")
    col4.metric(
        "Largest Mean-Median Gap",
        f"RM {max_gap_row['inequality_gap']:,.0f}",
        f"{max_gap_row['parlimen']}"
    )

    st.markdown("---")

    # 3. Three Visualizations
    # Viz 1: Histogram of Constituency Income Distribution
    st.subheader("Visualization 1: Distribution of Constituency Mean Income (Histogram)")
    fig1 = px.histogram(
        df_y,
        x="income_mean",
        color="region",
        nbins=25,
        barmode="stack",
        labels={"income_mean": "Mean Monthly Household Income (RM)", "region": "Region"},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig1.add_vline(
        x=avg_med,
        line_dash="dash",
        line_color="#1f77b4",
        annotation_text=f"Median: RM {avg_med:,.0f}",
        annotation_position="top left"
    )
    fig1.add_vline(
        x=avg_mean,
        line_dash="solid",
        line_color="#ff7f0e",
        annotation_text=f"Mean: RM {avg_mean:,.0f}",
        annotation_position="top right"
    )
    fig1.update_layout(
        yaxis_title="Number of Constituencies",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig1, use_container_width=True)

    c1, c2 = st.columns(2)

    # Viz 2: Dumbbell Plot (Mean vs Median Income by State)
    with c1:
        st.subheader("Visualization 2: Mean vs. Median Income Gap (Dumbbell Chart)")
        state_summary = (
            df_y.groupby("state")[["income_mean", "income_median"]]
            .mean()
            .reset_index()
            .sort_values("income_mean", ascending=True)
        )
        fig2 = go.Figure()
        for _, row in state_summary.iterrows():
            fig2.add_trace(go.Scatter(
                x=[row["income_median"], row["income_mean"]],
                y=[row["state"], row["state"]],
                mode="lines",
                line=dict(color="gray", width=2),
                showlegend=False
            ))
        fig2.add_trace(go.Scatter(
            x=state_summary["income_median"],
            y=state_summary["state"],
            mode="markers",
            name="Median Income",
            marker=dict(color="#1f77b4", size=10)
        ))
        fig2.add_trace(go.Scatter(
            x=state_summary["income_mean"],
            y=state_summary["state"],
            mode="markers",
            name="Mean Income",
            marker=dict(color="#ff7f0e", size=10)
        ))
        fig2.update_layout(
            xaxis_title="Monthly Household Income (RM)",
            yaxis_title="",
            height=520,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Viz 3: 3D Surface Plot (State x Survey Year x Mean Income)
    with c2:
        st.subheader("Visualization 3: Multi-Year State Income Trajectory (3D Surface Plot)")
        state_order = (
            df_econ[df_econ["year"] == max(years)]
            .groupby("state")["income_mean"]
            .mean()
            .sort_values()
            .index.tolist()
        )
        piv_surf = (
            df_econ.pivot_table(index="state", columns="year", values="income_mean", aggfunc="mean")
            .loc[state_order]
        )
        fig3 = go.Figure(data=[go.Surface(
            z=piv_surf.values,
            x=[str(y) for y in piv_surf.columns],
            y=piv_surf.index.tolist(),
            colorscale="Viridis",
            colorbar=dict(title="Mean Income (RM)")
        )])
        fig3.update_layout(
            scene=dict(
                xaxis_title="Survey Year",
                yaxis_title="State (Sorted)",
                zaxis_title="Mean Income (RM)"
            ),
            margin=dict(l=0, r=0, b=0, t=30),
            height=520
        )
        st.plotly_chart(fig3, use_container_width=True)

    # 4. Interpretation / Discussion
    st.subheader("Interpretation & Scientific Discussion")
    st.markdown(
        "- **Right-Skewed Income Distribution (Histogram):** The majority of Malaysian constituencies cluster between RM 4,500 and RM 7,500, while a long right tail of affluent urban constituencies pulls the national mean noticeably above the median.\n"
        "- **State-Level Skewness (Dumbbell Chart):** Across every state, mean income exceeds median income, with the widest internal gaps occurring in major economic hubs such as W.P. Kuala Lumpur and Selangor.\n"
        "- **Temporal & Spatial Income Surface (3D Surface Plot):** Tracing the 3D surface across 2019, 2022, and 2024 illustrates a steady upward shift in household income nationwide, alongside a steep elevation ridge separating Federal Territories from lower-income states."
    )

# =========================================================
# PAGE 2: HOUSEHOLD EXPENDITURE & SAVINGS CAPACITY
# =========================================================
elif page == "Page 2: Household Expenditure & Savings Capacity":
    st.title("Page 2: Cost-of-Living Pressure & Net Savings Capacity")

    # 1. Objective Statement
    st.info(
        "**Objective Statement:** To evaluate household expenditure burden and net monthly surplus "
        "across Malaysian states and constituencies, identifying regions facing the tightest cost-of-living squeeze."
    )

    df_y = df_econ[df_econ["year"] == selected_year]

    # 2. Summary Box
    st.subheader(f"Summary Box ({selected_year})")
    col1, col2, col3, col4 = st.columns(4)
    avg_exp = df_y["expenditure"].mean()
    avg_surplus = df_y["surplus_mean"].mean()
    avg_ratio = df_y["spending_ratio"].mean()
    lowest_surplus = df_y.loc[df_y["surplus_mean"].idxmin()]

    col1.metric("Avg Monthly Expenditure", f"RM {avg_exp:,.0f}")
    col2.metric("Avg Net Monthly Surplus", f"RM {avg_surplus:,.0f}")
    col3.metric("Avg Expenditure-to-Income", f"{avg_ratio:.1f}%")
    col4.metric(
        "Lowest Constituency Surplus",
        f"RM {lowest_surplus['surplus_mean']:,.0f}",
        f"{lowest_surplus['parlimen']}"
    )

    st.markdown("---")

    # 3. Three Visualizations
    # Viz 1: Annotated Heatmap of Expenditure-to-Income Ratio (%) across States & Years
    st.subheader("Visualization 1: Expenditure-to-Income Burden (%) Across States & Years (Heatmap)")
    piv_heat = (
        df_econ.pivot_table(index="state", columns="year", values="spending_ratio", aggfunc="mean")
        .sort_values(by=max(years), ascending=False)
    )
    piv_heat.columns = [str(c) for c in piv_heat.columns]

    fig1 = px.imshow(
        piv_heat,
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="Survey Year", y="State / Territory", color="Spend Ratio (%)")
    )
    fig1.update_layout(height=480)
    st.plotly_chart(fig1, use_container_width=True)

    c1, c2 = st.columns(2)

    # Viz 2: Top 10 vs Bottom 10 Constituencies by Net Surplus (Horizontal Bar)
    with c1:
        st.subheader("Visualization 2: Top 10 vs. Bottom 10 Constituencies by Surplus")
        top10 = df_y.nlargest(10, "surplus_mean").assign(Group="Top 10 Highest Surplus")
        bot10 = df_y.nsmallest(10, "surplus_mean").assign(Group="Bottom 10 Lowest Surplus")
        extremes = pd.concat([bot10, top10]).sort_values("surplus_mean", ascending=True)

        fig2 = px.bar(
            extremes,
            x="surplus_mean",
            y="parlimen",
            color="Group",
            orientation="h",
            hover_data=["state", "income_mean", "expenditure"],
            labels={"surplus_mean": "Net Monthly Surplus (RM)", "parlimen": "Constituency"},
            color_discrete_map={
                "Top 10 Highest Surplus": "#00CC96",
                "Bottom 10 Lowest Surplus": "#EF553B"
            }
        )
        fig2.update_layout(height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig2, use_container_width=True)

    # Viz 3: Scatter Plot (Mean Income vs Spending Ratio % — Engel's Law)
    with c2:
        st.subheader("Visualization 3: Income vs. Spending Burden (%) (Scatter Plot)")
        fig3 = px.scatter(
            df_y,
            x="income_mean",
            y="spending_ratio",
            color="region",
            hover_name="parlimen",
            hover_data=["state", "expenditure", "surplus_mean"],
            trendline="ols",
            labels={
                "income_mean": "Mean Monthly Income (RM)",
                "spending_ratio": "Expenditure-to-Income Ratio (%)",
                "region": "Region"
            },
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig3.update_layout(
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig3, use_container_width=True)

    # 4. Interpretation / Discussion
    st.subheader("Interpretation & Scientific Discussion")
    st.markdown(
        "- **Rising Cost-of-Living Heatmap (Heatmap):** Darker cells in 2022 and 2024 demonstrate a nationwide increase in expenditure-to-income ratios compared to 2019, with states like Kelantan, Negeri Sembilan, and Melaka dedicating over 71% of mean household income to consumption.\n"
        "- **Constituency Extremes (Horizontal Bar):** Top-surplus urban constituencies retain over RM 8,000/month after expenditure, whereas bottom-surplus rural constituencies operate with less than RM 1,000/month in residual income.\n"
        "- **Engel's Law Pattern (Scatter Plot):** A negative correlation between mean income and spending ratio confirms that lower-income constituencies dedicate a substantially larger share of earnings to basic consumption, leaving a thinner margin for savings."
    )

# =========================================================
# PAGE 3: POPULATION SCALE & REGIONAL DYNAMICS
# =========================================================
elif page == "Page 3: Population Scale & Regional Dynamics":
    st.title("Page 3: State Population Distribution, Growth & Regional Profiles")

    # 1. Objective Statement
    st.info(
        "**Objective Statement:** To analyze state-level population distribution and five-year demographic growth "
        "(2019–2024), examining how population scale relates to household income and consumption across Malaysian regions."
    )

    df_sy = df_state[df_state["year"] == selected_year].copy()

    # Calculate 2019 -> 2024 growth for KPI & Chart 2
    p_first = df_state[df_state["year"] == min(years)].set_index("state")["population"]
    p_last = df_state[df_state["year"] == max(years)].set_index("state")["population"]
    df_growth = pd.DataFrame({
        "state": p_last.index,
        "pop_2019": p_first.values,
        "pop_2024": p_last.values,
        "growth_pct": ((p_last - p_first) / p_first * 100).values
    }).sort_values("growth_pct", ascending=True)

    # 2. Summary Box
    st.subheader(f"Summary Box ({selected_year})")
    col1, col2, col3, col4 = st.columns(4)
    total_pop_m = df_sy["population"].sum() / 1000
    largest_row = df_sy.loc[df_sy["population"].idxmax()]
    fastest_row = df_growth.loc[df_growth["growth_pct"].idxmax()]
    corr_pop_inc = df_sy["population"].corr(df_sy["income_mean"])

    col1.metric("Total Malaysia Population", f"{total_pop_m:.2f} Million")
    col2.metric("Most Populous State", largest_row["state"], f"{largest_row['population']/1000:.2f} Million")
    col3.metric(
        f"Fastest Growth ({min(years)}–{max(years)})",
        fastest_row["state"],
        f"+{fastest_row['growth_pct']:.1f}%"
    )
    col4.metric("Pop–Income Correlation (r)", f"{corr_pop_inc:.2f}", "Weak linear link")

    st.markdown("---")

    # 3. Three Visualizations
    c1, c2 = st.columns(2)

    # Viz 1: Sunburst Chart (Population Share colored by Mean Income)
    with c1:
        st.subheader("Visualization 1: Population Share & Mean Income (Sunburst)")
        fig1 = px.sunburst(
            df_sy,
            path=[px.Constant("Malaysia"), "region", "state"],
            values="population",
            color="income_mean",
            color_continuous_scale="Blues",
            hover_data={"population": ":.1f", "income_mean": ":,.0f"},
            labels={"population": "Population ('000)", "income_mean": "Mean Income (RM)"}
        )
        fig1.update_layout(height=480)
        st.plotly_chart(fig1, use_container_width=True)

    # Viz 2: Horizontal Bar of 5-Year Population Growth (%)
    with c2:
        st.subheader(f"Visualization 2: State Population Growth ({min(years)} vs. {max(years)})")
        fig2 = px.bar(
            df_growth,
            x="growth_pct",
            y="state",
            orientation="h",
            color="growth_pct",
            color_continuous_scale="Teal",
            text=df_growth["growth_pct"].map(lambda v: f"+{v:.1f}%"),
            labels={"growth_pct": "Population Growth (%)", "state": "State / Territory"}
        )
        avg_growth = df_growth["growth_pct"].mean()
        fig2.add_vline(
            x=avg_growth,
            line_dash="dash",
            line_color="red",
            annotation_text=f"State Avg: +{avg_growth:.1f}%"
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(height=480, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Viz 3: Regional Population Share (Donut / Pie Chart)
    st.subheader("Visualization 3: Regional Share of National Population (Pie Chart)")
    reg_pop = (
        df_sy.groupby("region", as_index=False)["population"]
        .sum()
        .sort_values("population", ascending=False)
    )
    fig3 = px.pie(
        reg_pop,
        names="region",
        values="population",
        hole=0.35,
        color="region",
        color_discrete_map={
            "Peninsular Malaysia": "#636EFA",
            "East Malaysia": "#EF553B",
            "Federal Territory": "#00CC96"
        },
        labels={"population": "Population ('000)", "region": "Region"}
    )
    fig3.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Population: %{value:,.1f}k<br>Share: %{percent}<extra></extra>"
    )
    fig3.update_layout(height=440)
    st.plotly_chart(fig3, use_container_width=True)

    # 4. Interpretation / Discussion
    st.subheader("Interpretation & Scientific Discussion")
    st.markdown(
        "- **Population Concentration vs. Income (Sunburst):** Peninsular Malaysia accounts for the vast majority of the national population, with Selangor leading at 7.36 million, while high-income Federal Territories form compact demographic footprints.\n"
        "- **Divergent Growth Rates (Growth Bar Chart):** Between 2019 and 2024, Perlis (+16.9%), W.P. Putrajaya (+16.0%), and W.P. Kuala Lumpur (+16.0%) experienced the steepest percentage expansions, far outpacing slower-growing states.\n"
        "- **Regional Distribution (Pie Chart):** Over three-quarters of Malaysia's population resides in Peninsular Malaysia, followed by East Malaysia (~20%) and Federal Territories (~6%)—confirming that Federal Territories generate disproportionate economic output relative to their small population share."
    )
