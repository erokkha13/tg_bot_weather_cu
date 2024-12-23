import matplotlib.pyplot as plt
import pandas as pd
import uuid

def create_single_day_chart(temperatures, city_labels):
    plt.figure(figsize=(9, 5))
    plt.bar(city_labels, temperatures, color='limegreen')
    plt.xlabel('Названия городов')
    plt.ylabel('Температура (°C)')
    plt.title('Сравнение температур (1 день)')
    plt.xticks(rotation=45)

    filename = f'single_day_{uuid.uuid4()}.png'
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    return filename

def create_three_day_chart(cities_data):
    tmp_records = []
    for city, day_temp_list in cities_data.items():
        for date_str, tmp_val in day_temp_list[:3]:
            tmp_records.append({
                'Город': city,
                'Дата': date_str,
                'Температура': tmp_val
            })

    df = pd.DataFrame(tmp_records)

    plt.figure(figsize=(9, 5))
    for city_name in df['Город'].unique():
        subset = df[df['Город'] == city_name]
        plt.plot(subset['Дата'], subset['Температура'], marker='o', label=city_name)

    plt.title('Температура за 3 дня')
    plt.xlabel('Дата')
    plt.ylabel('Температура (°C)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()

    filename = f'three_day_{uuid.uuid4()}.png'
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    return filename

def create_five_day_chart(cities_data):
    tmp_records = []
    for city, day_temp_list in cities_data.items():
        for date_str, tmp_val in day_temp_list:
            tmp_records.append({
                'Город': city,
                'Дата': date_str,
                'Температура': tmp_val
            })

    df = pd.DataFrame(tmp_records)

    plt.figure(figsize=(9, 5))
    for city_name in df['Город'].unique():
        subset = df[df['Город'] == city_name]
        plt.plot(subset['Дата'], subset['Температура'], marker='o', label=city_name)

    plt.title('Температура за 5 дней')
    plt.xlabel('Дата')
    plt.ylabel('Температура (°C)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()

    filename = f'five_day_{uuid.uuid4()}.png'
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    return filename