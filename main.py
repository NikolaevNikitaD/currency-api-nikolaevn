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

# Разбиение на календарные годы, включая 31 декабря в високосные годы
def split_dates(start, end):
    dates = []
    current = start
    while current <= end:
        next_end = current + relativedelta(years=1) - timedelta(days=1)
        if next_end > end:
            next_end = end
        dates.append((current, next_end))

        # Добавляем 31 декабря отдельно, если год високосный и не включен в диапазон
        if is_leap_year(current.year) and next_end.month == 12 and next_end.day == 30:
            dates.append((next_end + timedelta(days=1), next_end + timedelta(days=1)))

        current = next_end + timedelta(days=1)
    return dates

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
        for s, e in split_dates(start, end):
            url = f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}?startDate={s.date()}&endDate={e.date()}"
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

    return jsonify(result_rows)
