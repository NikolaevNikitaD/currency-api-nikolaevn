import os
os.system("pip install python-dateutil")

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

app = Flask(__name__)

# ID валют НБРБ
CURRENCY_IDS = {
    "USD": 431,
    "EUR": 451,
    "RUB": 456,
    "CNY": 462
}

# Определение високосных лет
def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

# Получаем список високосных годов в диапазоне
def get_leap_years(start, end):
    leap_years = []
    for year in range(start.year, end.year + 1):
        if is_leap_year(year):
            leap_years.append(year)
    return leap_years

@app.route("/rates")
def rates():
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")

    if not start_str or not end_str:
        return jsonify(error="Нужны параметры start_date и end_date в формате YYYY-MM-DD"), 400

    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        if start > end:
            raise ValueError("Дата начала позже даты окончания")
    except Exception as e:
        return jsonify(error=f"Неверные даты: {str(e)}"), 400

    result_rows = []

    for name, cur_id in CURRENCY_IDS.items():
        # Основной запрос
        url = f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}?startDate={start.date()}&endDate={end.date()}"
        resp = requests.get(url)
        if resp.ok:
            try:
                data = resp.json()
                for entry in data:
                    result_rows.append({
                        "date": entry["Date"][:10],
                        "currency": name,
                        "rate": entry["Cur_OfficialRate"]
                    })
            except Exception as ex:
                return jsonify(error=f"Ошибка чтения данных для {name}: {str(ex)}"), 500
        else:
            return jsonify(error=f"Ошибка запроса к НБРБ для {name}: статус {resp.status_code}"), 502

        # Проверяем високосные годы и добавляем `год-12-31`
        leap_years = get_leap_years(start, end)
        for leap_year in leap_years:
            leap_date = f"{leap_year}-12-31"
            url = f"https://api.nbrb.by/exrates/rates/{cur_id}?ondate={leap_date}"
            resp = requests.get(url)
            if resp.ok:
                try:
                    data = resp.json()
                    result_rows.append({
                        "date": leap_date,
                        "currency": name,
                        "rate": data["Cur_OfficialRate"]
                    })
                except Exception as ex:
                    return jsonify(error=f"Ошибка чтения данных для {name} ({leap_date}): {str(ex)}"), 500
            else:
                return jsonify(error=f"Ошибка запроса к НБРБ для {name} ({leap_date}): статус {resp.status_code}"), 502

    return jsonify(result_rows)
