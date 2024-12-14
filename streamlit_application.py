import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go


def get_current_temperature(city_name, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['main']['temp'], None
    elif response.status_code == 401:
        return None, {"cod":401, "message": "Invalid API key. Please see https://openweathermap.org/faq#error401 for more info."}
    else:
        return None, f"Error: {response.status_code}."

def compute_statistics_and_anomaly(df, selected_city):
    city_data = df[df['city'] == selected_city]
    city_data['rolling_avg_30'] = city_data.groupby('season')['temperature'].transform(lambda x: x.rolling(window=30, min_periods=1).mean())
    city_data['seasonal_avg'] = city_data.groupby('season')['temperature'].transform('mean')
    city_data['seasonal_std'] = city_data.groupby('season')['temperature'].transform('std')
    city_data['anomaly'] = (city_data.temperature > city_data.seasonal_avg + city_data.seasonal_std * 2) | \
                           (city_data.temperature < city_data.seasonal_avg - city_data.seasonal_std * 2)
    
    return city_data

st.title("Temperature analysis on historical data and OpenWeatherMap API")


st.sidebar.header("Upload historical data here")
uploaded_file = st.sidebar.file_uploader("choose your CSV file", type="csv")


if uploaded_file:
    # собираем вводные
    data = pd.read_csv(uploaded_file)
    cities = data['city'].unique()
    selected_city = st.sidebar.selectbox("Choose city", cities)
    api_key = st.sidebar.text_input("Input your API key for OpenWeatherMap", type="password")

    #
    if selected_city:
        st.subheader(f"Data for city: {selected_city}")
        
        city_data = compute_statistics_and_anomaly(data, selected_city)

        st.write("Statistics on seasonal data:")
        st.write(city_data.describe())

    
        st.subheader("Time series of temperature with anomaly:")
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=city_data['timestamp'],
            y=city_data['temperature'],
            mode='lines',
            name='Temperature'
        ))

        anomalies = city_data[city_data['anomaly'] == True]
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'],
            y=anomalies['temperature'],
            mode='markers',
            name='Anomalies',
            marker=dict(color='red', size=8),
        ))

        st.plotly_chart(fig)
        st.subheader("Seasonal profile")
        seasonal_profile = city_data.groupby('season')[['temperature']].mean().reset_index()
        st.bar_chart(seasonal_profile, x='season', y='temperature')

        # вытаскиваем актуальную температуру по апи
        if api_key:
            current_temp, error = get_current_temperature(selected_city, api_key)
            if error:
                st.error(error)
            else:
                current_month = datetime.datetime.now().month
                current_season = None
                if current_month in [12, 1, 2]:
                    current_season = "winter"
                elif current_month in [3, 4, 5]:
                    current_season = "spring"
                elif current_month in [6, 7, 8]:
                    current_season = "summer"
                elif current_month in [9, 10, 11]:
                    current_season = "autumn"
                seasonal_data = city_data[city_data['season'] == current_season]
                seasonal_avg = seasonal_data['seasonal_avg'].iloc[0]
                seasonal_std = seasonal_data['seasonal_std'].iloc[0]
                is_normal = current_temp >= seasonal_avg - 2 * seasonal_std | current_temp <= seasonal_avg + 2 * seasonal_std

                st.subheader(f"Current temperature in city {selected_city}: {current_temp}C")
                if is_normal:
                    st.success("Current temperature is in normal interval for this season")
                else:
                    st.warning("Current temperature is abnormal for this season")