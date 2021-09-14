import json
import locale
from datetime import datetime, timedelta

import requests
from matplotlib import pyplot as plt

from settings import WEATHER_TOKEN


def get_weather_by_city(city):
    response = requests.get(
        'https://api.openweathermap.org/data/2.5/weather',
        params={
            'q': city,
            'appId': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru'
        }
    )
    return response.json()


def get_weather_by_location(latitude, longitude):
    response = requests.get(
        'https://api.openweathermap.org/data/2.5/weather',
        params={
            'lat': latitude,
            'lon': longitude,
            'appId': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru'
        }
    )
    return response.json()


def get_hourly_forecast(latitude, longitude):
    response = requests.get(
        'https://api.openweathermap.org/data/2.5/onecall',
        params={
            'lat': latitude,
            'lon': longitude,
            'appId': WEATHER_TOKEN,
            'exclude': 'current,minutely,daily,alerts',
            'units': 'metric',
            'lang': 'ru',
        }
    )
    return response.json()


if __name__ == '__main__':
    # print(get_hourly_forecast(55.7887, 49.1221))
    with open('responses/one_call_hourly.json') as f:
        data = json.load(f)
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    timezone_offset = data['timezone_offset']
    times = []
    dates = []
    temps = []

    for elem in data['hourly']:
        dt = datetime.utcfromtimestamp(elem['dt']) + timedelta(seconds=timezone_offset)
        temp = round(elem['temp'])
        times.append(dt.strftime('%H:%M'))
        dates.append(dt.strftime('%d %B'))
        temps.append(temp)

    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-darkgrid')
    plt.bar(range(len(temps)), temps)
    plt.xlabel('Время')
    plt.ylabel('Температура')
    plt.title(f'Прогноз погоды на 48 часов ({dates[0]} - {dates[-1]})')
    plt.xticks(range(len(temps)), times, rotation=60)

    plt.margins(x=0.01)
    plt.tight_layout()
    plt.show()
