import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
from src.trading.paper_broker import get_all_trades

# Set page configuration for wide layout and custom icon
st.set_page_config(
    page_title="Weather Prediction Market AI Agent",
    page_icon="cloud",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Mode / Sleek Glassmorphism look)
st.markdown("""
<style>
    .main {
        background-color: #0f1116;
        color: #e2e8f0;
    }
    .metric-card {
        background-color: #1a1f29;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #63b3ed;
        margin-top: 5px;
    }
    .metric-label {
        font-size: 14px;
        color: #a0aec0;
    }
</style>
""", unsafe_allow_html=True)

st.title("Weather Prediction Market AI Agent — Dashboard")
st.markdown("---")

trades = get_all_trades()

if not trades:
    st.info("No trades recorded yet. Run `python main.py` first to discover markets and place paper trades.")
else:
    df = pd.DataFrame(trades)
    
    # Preprocess columns
    if 'resolved' not in df.columns:
        df['resolved'] = 0
    if 'pnl' not in df.columns:
        df['pnl'] = 0.0
    if 'trade_type' not in df.columns:
        df['trade_type'] = 'primary'
    if 'llm_critique' not in df.columns:
        df['llm_critique'] = ''
        
    resolved_df = df[df['resolved'] == 1]
    unresolved_df = df[df['resolved'] == 0]
    
    # ------------------ SIDEBAR ------------------
    st.sidebar.header("Agent Parameters")
    st.sidebar.markdown(f"**Starting Bankroll:** $1000.00")
    st.sidebar.markdown(f"**Kelly Fraction:** 0.15 (15% Fractional)")
    st.sidebar.markdown(f"**Min Edge:** 6.0%")
    st.sidebar.markdown(f"**Max Exposure/City:** 10.0%")
    st.sidebar.markdown(f"**Hedge Trigger:** 8.0%")
    
    st.sidebar.header("Database Info")
    st.sidebar.text(f"Resolved Trades: {len(resolved_df)}")
    st.sidebar.text(f"Unresolved Trades: {len(unresolved_df)}")
    
    # ------------------ METRICS OVERVIEW ------------------
    st.subheader("Key Performance Metrics")
    
    # Calculate Brier Scores
    brier_model = 0.0
    brier_market = 0.0
    brier_msg = "No resolved primary trades yet."
    
    resolved_primary = resolved_df[resolved_df['trade_type'] == 'primary']
    if not resolved_primary.empty:
        model_errors = []
        market_errors = []
        for _, row in resolved_primary.iterrows():
            # Reconstruct actual YES outcome (1 if PnL > 0 for YES, or PnL < 0 for NO)
            if row['side'] == 'YES':
                actual_yes = 1 if row['pnl'] > 0 else 0
            else:
                actual_yes = 0 if row['pnl'] > 0 else 1
                
            model_errors.append((row['model_probability'] - actual_yes) ** 2)
            market_errors.append((row['price'] - actual_yes) ** 2)
            
        brier_model = np.mean(model_errors)
        brier_market = np.mean(market_errors)
        brier_msg = f"Model Brier: {brier_model:.4f} vs Market: {brier_market:.4f}"
        
    col1, col2, col3, col4 = st.columns(4)
    
    # Total Trades
    col1.metric("Total Positions", len(df), delta=f"+{len(unresolved_df)} active")
    
    # Total Staked
    col2.metric("Total Capital Staked", f"${df['stake'].sum():.2f}")
    
    # Total Portfolio PnL
    net_pnl = resolved_df['pnl'].sum()
    col3.metric("Net Portfolio PnL", f"${net_pnl:+.2f}", delta=f"{resolved_df['pnl'].sum():+.2f} USD")
    
    # Brier Accuracy
    if not resolved_primary.empty:
        delta_brier = brier_model - brier_market
        col4.metric(
            "Model Brier Score", 
            f"{brier_model:.4f}", 
            delta=f"{delta_brier:+.4f} (vs Market)", 
            delta_color="inverse" # Lower Brier score is better, so negative delta is good!
        )
    else:
        col4.metric("Model Brier Score", "N/A", help="Calculated after resolving trades using evaluate_results.py")

    # ------------------ LAYOUT SECTIONS ------------------
    tab1, tab2, tab3 = st.tabs(["Active Positions", "Resolved History", "LLM Analyser & Hedge Logs"])
    
    with tab1:
        st.subheader("Active & Unresolved Positions")
        if unresolved_df.empty:
            st.info("No active unresolved positions right now. Run evaluate_results.py to resolve past events.")
        else:
            display_unresolved = unresolved_df[['timestamp', 'city', 'question', 'side', 'price', 'model_probability', 'stake', 'trade_type', 'target_date']].copy()
            st.dataframe(display_unresolved, use_container_width=True)
            
    with tab2:
        st.subheader("Resolved Prediction History")
        if resolved_df.empty:
            st.info("No resolved trades yet. Run `python evaluate_results.py` to resolve past predictions using historical weather data.")
        else:
            display_resolved = resolved_df[['timestamp', 'city', 'question', 'side', 'price', 'model_probability', 'actual_temp', 'pnl', 'trade_type']].copy()
            st.dataframe(display_resolved, use_container_width=True)
            
            # Exposure Chart
            st.subheader("PnL Distribution by City")
            city_pnl = resolved_df.groupby('city')['pnl'].sum()
            st.bar_chart(city_pnl)

    with tab3:
        st.subheader("Risk Analyst LLM Critiques")
        st.markdown("Below are the detailed skepticism logs and risk assessments generated by the LLM layer for each trade.")
        
        # Display the 10 most recent trades with critiques
        recent_trades_with_critiques = df[df['llm_critique'] != ''].sort_values('timestamp', ascending=False)
        
        if recent_trades_with_critiques.empty:
            st.info("No LLM reviews logged yet. Make sure your OPENROUTER_API_KEY is configured in your .env file.")
        else:
            for idx, row in recent_trades_with_critiques.head(10).iterrows():
                trade_status = "RESOLVED" if row['resolved'] == 1 else "ACTIVE"
                pnl_indicator = f" (PnL: ${row['pnl']:+.2f})" if row['resolved'] == 1 else ""
                
                with st.expander(f"{trade_status} | {row['city']} ({row['target_date']}) - {row['question']}{pnl_indicator}"):
                    col_l, col_r = st.columns([1, 2])
                    with col_l:
                        st.markdown(f"**Position Type:** {row['trade_type'].upper()}")
                        st.markdown(f"**Side:** {row['side']}")
                        st.markdown(f"**Stake:** ${row['stake']:.2f}")
                        st.markdown(f"**Consensus Implied Prob (Market Price):** {row['price']:.1%}")
                        st.markdown(f"**Our Model Probability:** {row['model_probability']:.1%}")
                    with col_r:
                        st.markdown(f"**Mathematical Rationale:**\n*{row['rationale']}*")
                        st.markdown(f"**LLM Risk Critique:**\n> {row['llm_critique']}")