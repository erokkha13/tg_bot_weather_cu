import requests

class WeatherEngine:
    URL_LOCATION_SEARCH = 'http://dataservice.accuweather.com/locations/v1/cities/search'
    URL_1DAY_FORECAST = 'http://dataservice.accuweather.com/forecasts/v1/daily/1day/'
    URL_5DAY_FORECAST = 'http://dataservice.accuweather.com/forecasts/v1/daily/5day/'

    def __init__(self, api_key):
        self.api_key = api_key

    def retrieveGeoCoordinates(self, city_name):
        try:
            params = {
                'apikey': self.api_key,
                'q': city_name
            }
            resp = requests.get(self.URL_LOCATION_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
            lat = data[0]['GeoPosition']['Latitude']
            lon = data[0]['GeoPosition']['Longitude']
            return (lat, lon)
        except requests.exceptions.RequestException as ex:
            raise Exception(f"Проблема с получением координат: {ex}")

    def retrieveCityId(self, city_name):
        try:
            params = {
                'apikey': self.api_key,
                'q': city_name
            }
            resp = requests.get(self.URL_LOCATION_SEARCH, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data[0]['Key']
        except requests.exceptions.RequestException as ex:
            raise Exception(f"Ошибка при запросе кода города: {ex}")

    def gatherWeather(self, city_id, day_option):
        try:
            if day_option == '1day':
                return self._fetchDaily(city_id)
            elif day_option in ['3day', '5day']:
                return self._fetchExtended(city_id, day_option)
        except requests.exceptions.RequestException as ex:
            raise Exception(f"Ошибка запроса прогноза: {ex}")

    def _fetchDaily(self, city_id):
        params = {
            'apikey': self.api_key,
            'details': 'true',
            'metric': 'true'
        }
        resp = requests.get(self.URL_1DAY_FORECAST + city_id, params=params)
        resp.raise_for_status()
        json_data = resp.json()['DailyForecasts'][0]

        result = {
            'date': json_data['Date'][:10],
            'temp': json_data['RealFeelTemperatureShade']['Minimum']['Value'],
            'humidity': json_data['Day']['RelativeHumidity']['Average'],
            'wind_speed': json_data['Day']['Wind']['Speed']['Value'],
            'precipitation_probability': json_data['Day']['PrecipitationProbability']
        }
        return result

    def _fetchExtended(self, city_id, time_range):
        params = {
            'apikey': self.api_key,
            'details': 'true',
            'metric': 'true'
        }
        resp = requests.get(self.URL_5DAY_FORECAST + city_id, params=params)
        resp.raise_for_status()

        data = resp.json()['DailyForecasts']
        limit = 3 if time_range == '3day' else 5
        forecasts = []
        for idx in range(limit):
            day_info = data[idx]
            forecasts.append({
                'date': day_info['Date'][:10],
                'temp': day_info['RealFeelTemperatureShade']['Minimum']['Value'],
                'humidity': day_info['Day']['RelativeHumidity']['Average'],
                'wind_speed': day_info['Day']['Wind']['Speed']['Value'],
                'precipitation_probability': day_info['Day']['PrecipitationProbability']
            })
        return forecasts

    def evaluate_weather(self, temperature, humidity, wind_speed, precip_chance):
        rules = [
            ("На улице слишком холодно, рекомендуется оставаться дома", temperature <= -40),
            ("Сильный шторм ожидается, соблюдайте осторожность", wind_speed >= 75),
            ("Погода хорошая: умеренный ветер, тепло и маловероятен дождь",
             11 <= wind_speed < 30 and 15 < temperature < 25 and precip_chance < 30),
            ("Температура высокая, будьте осторожны при выходе", temperature > 40 and precip_chance < 30),
            ("Жаркая погода с вероятностью дождя, рекомендуем взять зонт",
             temperature > 40 and 30 <= precip_chance <= 75),
            ("Очень высокая температура и большой шанс дождя, стоит оставаться дома",
             temperature > 40 and precip_chance > 75),
            ("Прохладно, но возможен дождь — одевайтесь по сезону и берите зонт",
             0 <= temperature <= 15 and wind_speed <= 20 and precip_chance > 50),
            ("Прохладно, дождь маловероятен, но стоит надеть легкую верхнюю одежду",
             0 <= temperature <= 15 and wind_speed <= 20),
            ("Ветер сильный, температура низкая — лучше остаться дома", 0 <= temperature <= 15 and wind_speed > 20),
            ("Температура ниже нуля и дождь — хороший повод для катания на коньках",
             temperature < 0 and precip_chance > 70),
            ("Минусовая температура и сильный ветер — рекомендуем оставаться внутри",
             temperature < 0 and wind_speed >= 40),
            ("Температура ниже нуля, но относительно комфортно", temperature < 0),
            ("Дождь с умеренным ветром и приятной температурой, будьте готовы к изменениям",
             15 < temperature <= 40 and precip_chance > 55 and wind_speed <= 20),
            ("Дождь и ветер — неблагоприятные условия", 15 < temperature <= 40 and precip_chance > 55),
            ("Умеренный ветер с отсутствием дождя — зависит от ваших предпочтений",
             15 < temperature <= 40 and precip_chance <= 55 and wind_speed <= 20),
            ("Умеренный ветер без дождя — выбор за вами", 15 < temperature <= 40 and wind_speed > 20),
            ("Не могу точно оценить погоду, условия неопределенные", True)
        ]

        for advice, condition in rules:
            if condition:
                return advice