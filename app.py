#app.py
"""
Rally Racing App - Bootcamp Project
This connects to Snowflake and manages rally races with teams and cars.
It can setup tables, run races, and track results.

By: Giga Shubitidze
"""

import os
import traceback

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas



# Helpers


def load_env() -> None:
    """
    Load environment variables from the .env file.
    This lets us keep Snowflake credentials (user, password, etc.)
    outside of the code so they are safe.
    """
    load_dotenv()


def get_snowflake_connection(initial: bool = False):
    """
    Connect to Snowflake using environment variables.

    If initial=True, connect only with account, user, password (used for setup).
    Otherwise include warehouse, database, and schema (used for main operations).
    """
    if initial:
        args = {
            'user': os.getenv("SNOWFLAKE_USER"),
            'password': os.getenv("SNOWFLAKE_PASSWORD"),
            'account': os.getenv("SNOWFLAKE_ACCOUNT")
        }
    else:
        args = {
            'user': os.getenv("SNOWFLAKE_USER"),
            'password': os.getenv("SNOWFLAKE_PASSWORD"),
            'account': os.getenv("SNOWFLAKE_ACCOUNT"),
            'warehouse': os.getenv("SNOWFLAKE_WAREHOUSE"),
            'database': os.getenv("SNOWFLAKE_DATABASE"),
            'schema': os.getenv("SNOWFLAKE_SCHEMA")
        }
    return snowflake.connector.connect(**args)


def setup_snowflake(commands_file: str = 'setup.sql') -> None:
    """
    Run the SQL setup file (setup.sql) to create all tables, warehouse,
    and insert initial data.

    The function opens the file, splits by semicolons, and executes
    each SQL statement in Snowflake.
    """
    conn = get_snowflake_connection(initial=True)
    cursor = conn.cursor()

    with open(commands_file, 'r') as file:
        sql_commands = file.read()

    # split by ; so we can execute multiple commands
    sql_commands = sql_commands.split(';')
    for command in sql_commands:
        if command.strip():
            cursor.execute(command)

    cursor.close()
    conn.close()
    print("✅ Snowflake setup complete.")


def add_team(team_name: str, budget: float):
    """
    Add a new racing team to the TEAMS table.
    Returns (success, message).
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        # Check if team exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM BOOTCAMP_RALLY.RALLY.TEAMS 
            WHERE TEAM_NAME = %s
        """, (team_name,))
        if cursor.fetchone()[0] > 0:
            return False, f"🚫 Team with name '{team_name}' already exists."

        # Insert new team
        cursor.execute("""
            INSERT INTO BOOTCAMP_RALLY.RALLY.TEAMS (TEAM_NAME, BUDGET)
            VALUES (%s, %s)
        """, (team_name, float(budget)))
        conn.commit()
        return True, f"✅ Team '{team_name}' created successfully with budget {budget}."
    except Exception as e:
        conn.rollback()
        return False, f"🚨 Could not add team. Reason: {e}"
    finally:
        cursor.close()
        conn.close()


def add_car(car_name: str, speed: float, pit_stop_interval: float, pit_stop_duration: float, team_name: str):
    """
    Add a new car to the CARS table.
    Returns (success, message).
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        # Lookup team_id
        cursor.execute("""
            SELECT TEAM_ID
            FROM BOOTCAMP_RALLY.RALLY.TEAMS 
            WHERE TEAM_NAME = %s
        """, (team_name,))
        result = cursor.fetchone()
        if not result:
            return False, f"🚫 No team found with name '{team_name}'."
        team_id = result[0]

        # Check if car name already exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM BOOTCAMP_RALLY.RALLY.CARS 
            WHERE CAR_NAME = %s
        """, (car_name,))
        if cursor.fetchone()[0] > 0:
            return False, f"🚫 Car with name '{car_name}' already exists."

        # Insert car
        cursor.execute("""
            INSERT INTO BOOTCAMP_RALLY.RALLY.CARS 
                (CAR_NAME, SPEED, PIT_STOP_INTERVAL, PIT_STOP_DURATION, TEAM_ID)
            VALUES (%s, %s, %s, %s, %s)
        """, (car_name, float(speed), float(pit_stop_interval), float(pit_stop_duration), int(team_id)))
        conn.commit()
        return True, f"✅ Car '{car_name}' added successfully to team '{team_name}'."
    except Exception as e:
        conn.rollback()
        return False, f"🚨 Could not add car. Reason: {e}"
    finally:
        cursor.close()
        conn.close()



def start_race(distance,fee) -> None:
    """
    Start a rally race simulation:
      1. Create a new race event in RACE_EVENTS.
      2. Select all cars whose teams can afford the fee.
      3. Deduct participation fee from each team's budget.
      4. Insert race entries (car, team, race_id, time taken).
      5. Calculate results (position, prize money).
      6. Insert results and update team budgets with prize money.
      7. Commit all actions as one transaction (rollback if failure).
    """
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # 1. Create a race event row
        cursor.execute("INSERT INTO BOOTCAMP_RALLY.RALLY.RACE_EVENTS (DISTANCE) VALUES (%s)", (distance,))
        cursor.execute("SELECT RACE_ID FROM BOOTCAMP_RALLY.RALLY.RACE_EVENTS ORDER BY STARTED_AT DESC LIMIT 1")
        race_id = cursor.fetchone()[0]

        # 2. Select cars with enough team budget
        cursor.execute("""
            SELECT c.CAR_ID, c.CAR_NAME, c.SPEED, c.PIT_STOP_INTERVAL, c.PIT_STOP_DURATION,
                   c.TEAM_ID, t.TEAM_NAME, t.BUDGET
            FROM BOOTCAMP_RALLY.RALLY.CARS c
            JOIN BOOTCAMP_RALLY.RALLY.TEAMS t ON c.TEAM_ID = t.TEAM_ID
            WHERE t.BUDGET >= %s
        """, (fee,))
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=cols)

        if df.empty:
            raise Exception("🚫 No teams with enough budget to join this race.")

        # 3. Deduct fee from each team budget
        for team_id in df['TEAM_ID'].unique():
            try:
                cursor.execute("""
                    UPDATE BOOTCAMP_RALLY.RALLY.TEAMS 
                    SET BUDGET = BUDGET - %s 
                    WHERE TEAM_ID = %s
                """, (float(fee), int(team_id)))
            except:
                traceback.print_exc()

        # 4. Race entries table
        df_entries = df.copy()
        df_entries['RACE_ID'] = race_id
        df_entries['FEE'] = fee
        df_entries['TIME_TAKEN'] = (distance / df_entries["SPEED"] * 3600) + \
                                   (distance // df_entries["PIT_STOP_INTERVAL"] * df_entries['PIT_STOP_DURATION'])

        entries_df = df_entries[['RACE_ID', 'TEAM_ID', 'CAR_ID', 'TIME_TAKEN', 'FEE']]
        write_pandas(conn, entries_df, 'RACE_ENTRIES', schema='RALLY')

        # 5. Race results (positions + prizes)
        df_results = df_entries.copy()
        df_results['POSITION'] = df_results['TIME_TAKEN'].rank(method='min').astype(int)

        total_pot = df_results['FEE'].sum()
        prize_split = {1: 0.5, 2: 0.3, 3: 0.2}  # simple split
        df_results['PRIZE_MONEY'] = df_results['POSITION'].map(
            lambda pos: total_pot * prize_split.get(pos, 0)
        )

        results_df = df_results[['RACE_ID', 'TEAM_ID', 'CAR_ID', 'POSITION', 'PRIZE_MONEY']]
        write_pandas(conn, results_df, 'RACE_RESULTS', schema='RALLY')

        # 6. Update team budgets with prize money
        for _, row in results_df.iterrows():
            if row['PRIZE_MONEY'] > 0:
                try:
                    cursor.execute("""
                        UPDATE BOOTCAMP_RALLY.RALLY.TEAMS 
                        SET BUDGET = BUDGET + %s 
                        WHERE TEAM_ID = %s
                    """, (row['PRIZE_MONEY'], row['TEAM_ID']))
                except:
                    traceback.print_exc()
        # 7. Commit all actions
        conn.commit()
        print(f"✅ Race {race_id} completed successfully.")
        return race_id
    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        print(f"🚨 Race aborted, rolled back. Reason: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# Run as script

def is_snowflake_setup_needed():
    """
    Check if Snowflake setup has already been completed by testing
    if the required tables exist.

    Returns True if setup is needed, False otherwise.
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'RALLY' 
            AND TABLE_NAME IN ('TEAMS', 'CARS', 'RACE_EVENTS', 'RACE_ENTRIES', 'RACE_RESULTS')
        """)
        tables_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return tables_count < 5  # If we don't have all 5 tables, setup is needed
    except Exception:
        # If connection fails or query fails, likely setup is needed
        return True

# Run as script
if __name__ == "__main__":
    load_env()
    if is_snowflake_setup_needed():
        setup_snowflake()

    # Add a new team
    add_team("Turbo Titans", 45000.0)

    # Add a car for this team
    add_car("Nitro Beast", 205.0, 46.0, 11.5, "Turbo Titans")  # Assuming this new team gets TEAM_ID = 4

    # Start a race
    start_race(1000,100)
