# streamlit_app.py
"""
This is the Streamlit interface for the rally racing project.
It connects to Snowflake (via app.py functions) and lets users:
Add racing teams and cars
View current teams and cars
Start a rally race and see the results
"""

import streamlit as st
import pandas as pd
import traceback
import plotly.express as px
from app import load_env, get_snowflake_connection, add_team, add_car, start_race, is_snowflake_setup_needed, \
    setup_snowflake

# Load env variables
load_env()

st.set_page_config(page_title="🏁 Bootcamp Rally Manager", layout="wide")

st.title("🏁 Bootcamp Rally Racing Management App")

if is_snowflake_setup_needed():
    setup_snowflake()
# Helper: run SQL and return dataframe

def run_query(query: str, params=None):
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        traceback.print_exc()
        st.error(f"Query failed: {e}")
        return pd.DataFrame()
    finally:
        cur.close()
        conn.close()



# Sidebar navigation

menu = st.sidebar.radio("Navigation", ["Teams", "Cars", "Race Simulation"])


# Teams management

if menu == "Teams":
    st.subheader("👥 Teams Overview")

    df_teams = run_query("SELECT * FROM BOOTCAMP_RALLY.RALLY.TEAMS")
    st.dataframe(df_teams)

    st.subheader("➕ Add New Team")
    with st.form("add_team_form"):
        team_name = st.text_input("Team Name")
        budget = st.number_input("Starting Budget (USD)", min_value=500.0, step=500.0)
        submitted = st.form_submit_button("Add Team")
        if submitted and team_name:
            success, msg = add_team(team_name, budget)
            if success:
                st.success(msg)
            else:
                st.error(msg)



# Cars management

elif menu == "Cars":
    st.subheader("🚗 Cars Overview")

    df_cars = run_query("""
        SELECT c.CAR_ID, c.CAR_NAME, c.SPEED, c.PIT_STOP_INTERVAL, c.PIT_STOP_DURATION, t.TEAM_NAME
        FROM BOOTCAMP_RALLY.RALLY.CARS c
        JOIN BOOTCAMP_RALLY.RALLY.TEAMS t ON c.TEAM_ID = t.TEAM_ID
    """)
    st.dataframe(df_cars)

    st.subheader("➕ Add New Car")
    with st.form("add_car_form"):
        car_name = st.text_input("Car Name")
        speed = st.number_input("Speed (km/h)", min_value=50.0, max_value=500.0, step=1.0)
        pit_interval = st.number_input("Pit Stop Interval (km)", min_value=10.0, step=1.0)
        pit_duration = st.number_input("Pit Stop Duration (s)", min_value=5.0, step=0.5)

        teams_df = run_query("SELECT TEAM_NAME FROM BOOTCAMP_RALLY.RALLY.TEAMS")
        team_name = st.selectbox("Assign to Team", teams_df["TEAM_NAME"] if not teams_df.empty else [])

        submitted = st.form_submit_button("Add Car")
        if submitted and car_name and team_name:
            success, msg = add_car(car_name, speed, pit_interval, pit_duration, team_name)
            if success:
                st.success(msg)
            else:
                st.error(msg)




# Race simulation

elif menu == "Race Simulation":
    st.subheader("🏎️ Start Race")
    distance = st.number_input("Distance (km)", min_value=10, max_value=1000000, value=100, step=1)
    fee = st.number_input("Entry Fee (USD)", min_value=100, max_value=10000, value=1000, step=100)
    if st.button("Start Rally!"):
        try:
            with st.spinner("🏎️ Race in progress... Vrooom!"):
                latest_race_id = start_race(distance=distance, fee=fee)
            st.success("✅ Race completed successfully.")

            # Add visualization of last race results
            if latest_race_id:
                st.subheader("🏎️ Last Race Visualization")

                race_details = run_query("""
                    SELECT t.TEAM_NAME, c.CAR_NAME, e.TIME_TAKEN, r.POSITION 
                    FROM BOOTCAMP_RALLY.RALLY.RACE_RESULTS r
                    JOIN BOOTCAMP_RALLY.RALLY.RACE_ENTRIES e 
                      ON r.RACE_ID = e.RACE_ID 
                     AND r.CAR_ID = e.CAR_ID
                    JOIN BOOTCAMP_RALLY.RALLY.TEAMS t ON r.TEAM_ID = t.TEAM_ID
                    JOIN BOOTCAMP_RALLY.RALLY.CARS c ON r.CAR_ID = c.CAR_ID
                    WHERE r.RACE_ID = %s
                    ORDER BY r.POSITION ASC
                """, (int(latest_race_id),))

                if not race_details.empty:
                    race_details['LABEL'] = race_details['TEAM_NAME'] + ' - ' + race_details['CAR_NAME']
                    race_details['TIME_TAKEN_MIN'] = race_details['TIME_TAKEN'] / 60.0  # seconds → minutes

                    # Podium view
                    podium = race_details.head(3).copy()
                    podium['MEDAL'] = podium['POSITION'].map({1: "🥇", 2: "🥈", 3: "🥉"})
                    st.markdown("### 🏆 Podium")
                    for _, row in podium.iterrows():
                        st.write(
                            f"{row['MEDAL']} **{row['TEAM_NAME']}** ({row['CAR_NAME']}) — {row['TIME_TAKEN_MIN']:.2f} min")

                    # Race chart with plotly (better styling than st.bar_chart)
                    

                    fig = px.bar(
                        race_details.sort_values("POSITION"),
                        x="TIME_TAKEN_MIN",
                        y="LABEL",
                        color="TEAM_NAME",
                        text=race_details["TIME_TAKEN_MIN"].apply(lambda x: f"{x:.4f} min"),
                        orientation="h",
                        title="Race Finish Times"
                    )
                    fig.update_layout(
                        xaxis_title="Time Taken (minutes)",
                        yaxis_title="Team - Car",
                        showlegend=True,
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Add a position indicator
                    st.write(
                        "🏆 Winner: " + race_details.iloc[0]['TEAM_NAME'] + " - " + race_details.iloc[0]['CAR_NAME'])
        except Exception as e:
            st.error(str(e))

    st.subheader("📊 Race Results")
    df_results = run_query("""
        SELECT r.RACE_ID, t.TEAM_NAME, c.CAR_NAME, r.POSITION, r.PRIZE_MONEY
        FROM BOOTCAMP_RALLY.RALLY.RACE_RESULTS r
        JOIN BOOTCAMP_RALLY.RALLY.TEAMS t ON r.TEAM_ID = t.TEAM_ID
        JOIN BOOTCAMP_RALLY.RALLY.CARS c ON r.CAR_ID = c.CAR_ID
        ORDER BY r.RACE_ID DESC, r.POSITION ASC
    """)
    st.dataframe(df_results)

    st.subheader("💰 Updated Team Budgets")
    df_budgets = run_query("SELECT TEAM_NAME, BUDGET FROM BOOTCAMP_RALLY.RALLY.TEAMS")
    st.dataframe(df_budgets)
