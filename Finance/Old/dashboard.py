"""Streamlit dashboard for accounting system."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from core.db import init_db, get_session
from core.queries import DashboardQueries
from core.models import LogEntry
from sqlalchemy import func


st.set_page_config(page_title="Accounting Dashboard", layout="wide")


def init_session_state():
    """Initialize Streamlit session state."""
    if "db_init" not in st.session_state:
        init_db()
        st.session_state.db_init = True


def get_queries():
    """Get DashboardQueries instance."""
    return DashboardQueries(get_session())


# ============================================================================
# MAIN APP
# ============================================================================

st.title("📊 Accounting & Inventory Dashboard")

init_session_state()
queries = get_queries()

# Top-level KPIs
st.markdown("## Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

kpis = queries.get_kpis()

with col1:
    st.metric(
        label="Total Products",
        value=kpis["total_products"]
    )

with col2:
    st.metric(
        label="Units On Hand",
        value=kpis["total_units_on_hand"]
    )

with col3:
    st.metric(
        label="Inventory Value",
        value=f"${kpis['inventory_value']:,.2f}"
    )

with col4:
    st.metric(
        label="Total Logs",
        value=kpis["total_logs"]
    )

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(
    ["Products", "Low Stock", "Recent Logs", "Sales Analysis"]
)

# ============================================================================
# TAB 1: Products
# ============================================================================
with tab1:
    st.markdown("### All Products")
    
    products = queries.get_all_products()
    
    if products:
        df_products = pd.DataFrame(products)
        df_products["Total Value"] = (
            df_products["on_hand"] * df_products["unit_price"].fillna(0)
        )
        
        # Display table
        st.dataframe(
            df_products[["sku", "barcode", "name", "on_hand", "unit_price", "Total Value"]],
            use_container_width=True
        )
    else:
        st.info("No products found")

# ============================================================================
# TAB 2: Low Stock
# ============================================================================
with tab2:
    st.markdown("### Low Stock Alert")
    
    threshold = st.slider("Stock Threshold", min_value=1, max_value=100, value=10)
    low_stock = queries.get_low_stock_products(threshold=threshold)
    
    if low_stock:
        df_low = pd.DataFrame(low_stock)
        
        # Color code by severity
        st.dataframe(df_low, use_container_width=True)
        
        # Bar chart
        fig = px.bar(
            df_low,
            x="sku",
            y="on_hand",
            title="Low Stock Products",
            color="on_hand",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success(f"✓ All products above threshold ({threshold} units)")

# ============================================================================
# TAB 3: Recent Logs
# ============================================================================
with tab3:
    st.markdown("### Recent Activity")
    
    limit = st.slider("Show last N logs", min_value=10, max_value=100, value=20)
    logs = queries.get_recent_logs(limit=limit)
    
    if logs:
        df_logs = pd.DataFrame(logs)
        df_logs["created_at"] = pd.to_datetime(df_logs["created_at"])
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            selected_types = st.multiselect(
                "Filter by Log Type",
                options=df_logs["log_type"].unique().tolist(),
                default=df_logs["log_type"].unique().tolist()
            )
        
        with col2:
            date_range = st.date_input(
                "Date Range",
                value=[
                    (datetime.now() - timedelta(days=30)).date(),
                    datetime.now().date()
                ],
                max_value=datetime.now().date()
            )
        
        # Filter
        df_filtered = df_logs[
            (df_logs["log_type"].isin(selected_types)) &
            (df_logs["created_at"].dt.date >= date_range[0]) &
            (df_logs["created_at"].dt.date <= date_range[1])
        ]
        
        st.dataframe(
            df_filtered[["id", "created_at", "log_type", "ref_no", "counterparty"]],
            use_container_width=True
        )
    else:
        st.info("No logs found")

# ============================================================================
# TAB 4: Sales Analysis
# ============================================================================
with tab4:
    st.markdown("### Sales Summary")
    
    sales = queries.get_sales_summary(limit=100)
    
    if sales:
        df_sales = pd.DataFrame(sales)
        df_sales["created_at"] = pd.to_datetime(df_sales["created_at"])
        df_sales = df_sales.sort_values("created_at", ascending=False)
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Total Sales (count)",
                len(df_sales)
            )
        
        with col2:
            st.metric(
                "Total Revenue",
                f"${df_sales['amount'].sum():,.2f}"
            )
        
        with col3:
            st.metric(
                "Avg Sale",
                f"${df_sales['amount'].mean():,.2f}"
            )
        
        # Sales over time chart
        df_daily = df_sales.groupby(df_sales["created_at"].dt.date)["amount"].sum().reset_index()
        
        fig = px.line(
            df_daily,
            x="created_at",
            y="amount",
            title="Daily Sales",
            labels={"amount": "Revenue ($)", "created_at": "Date"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent sales table
        st.subheader("Recent Sales Details")
        st.dataframe(
            df_sales[["created_at", "sku", "qty", "amount", "customer"]],
            use_container_width=True
        )
    else:
        st.info("No sales found")

# Footer
st.markdown("---")
st.markdown(
    "🔧 *Built with Streamlit | Data stored in SQLite | Last updated: "
    + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "*"
)
