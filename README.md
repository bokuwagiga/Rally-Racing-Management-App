# Rally Racing Management App

A fully-featured application for managing rally racing events, teams, cars, and race simulations. Built with Python, Streamlit, and Snowflake for persistent data storage.

## 🏁 Features

- **Team Management**: Create racing teams with customizable budgets
- **Car Configuration**: Add cars with realistic performance parameters (speed, pit stop intervals)
- **Race Simulation**: Run realistic rally races with dynamic timing calculations
- **Financial Tracking**: Automatic budget management for entry fees and prize money
- **Race Visualization**: Interactive charts showing race results and team performance
- **Complete Database**: Persistent storage of all racing data in Snowflake

## 📋 Prerequisites

- Python 3.7+
- Snowflake account
- Git

## 🔧 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/bokuwagiga/Rally-Racing-Management-App.git
   cd Rally-Racing-Management-App
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp example.env .env
   ```

4. Edit the `.env` file with your Snowflake credentials:
   ```
   SNOWFLAKE_USER=your_username
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_ACCOUNT=your_account_identifier
   SNOWFLAKE_WAREHOUSE=WH_RALLY
   SNOWFLAKE_DATABASE=BOOTCAMP_RALLY
   SNOWFLAKE_SCHEMA=RALLY
   ```

## ⚙️ Snowflake Setup

1. Run the initial setup script to create required Snowflake objects:
   ```bash
   python app.py
   ```

   This will:
   - Create a warehouse named `WH_RALLY`
   - Create database `BOOTCAMP_RALLY`
   - Create tables for teams, cars, race events, and results
   - Insert sample data

## 🚀 Running the Application

Launch the Streamlit interface:
```bash
streamlit run streamlit_app.py
```

The web interface will open in your browser with three main sections:
- **Teams**: View and add racing teams
- **Cars**: View and add cars with custom performance characteristics
- **Race Simulation**: Start races and view results with visualizations

## 📁 Project Structure

- `app.py` - Core application logic and Snowflake integration
- `streamlit_app.py` - Web interface built with Streamlit
- `setup.sql` - SQL commands for database initialization
- `requirements.txt` - Required Python packages
- `example.env` - Template for environment variables

## 📝 Usage Guide

1. **Add Teams**: Navigate to the Teams section to create racing teams with starting budgets
2. **Add Cars**: In the Cars section, create cars with specific performance parameters
3. **Run Races**: Go to Race Simulation to set up and run rally races
4. **View Results**: After each race, see visualizations of performance and updated budgets

## 🌐 Deployment

For production deployment:

1. Create a proper Snowflake account with appropriate permissions
2. Consider using Streamlit Sharing or Streamlit Cloud for hosting the UI
3. Use environment variables for all sensitive information

---

Created by Giga Shubitidze as a bootcamp project.