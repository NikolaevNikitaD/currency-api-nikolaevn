import os
os.system("pip install python-dateutil")

from flask import Flask, request, jsonify
from datetime import datetime
import requests

app = Flask(__name__)

# Таблица с ID и цифровыми кодами валют
CURRENCIES = {
    "USD": {"id": 431, "code": 840},
    "EUR": {"id": 451, "code": 978},
    "RUB": {"id": 456, "code": 643},
    "CNY": {"id": 462, "code": 156},
    "GBP": {"id": 429, "code": 826},
    "CHF": {"id": 426, "code": 756}
}

# Определение високосного года
def is_leap_year(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

@app.route("/rates")
def rates():
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")
    currencies_str = request.args.get("currencies")

    if not start_str or not end_str or not currencies_str:
        return jsonify(error="Нужны параметры start_date, end_date и currencies (например, currencies=USD,EUR)"), 400

    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
        if start > end:
            raise ValueError("Дата начала позже даты окончания")
    except Exception as e:
        return jsonify(error=f"Неверные даты: {str(e)}"), 400

    currencies = currencies_str.split(",")
    result_rows = []

    for name in currencies:
        currency = CURRENCIES.get(name.strip())
        if not currency:
            return jsonify(error=f"Неизвестная валюта: {name}"), 400

        cur_id = currency["id"]
        cur_code = currency["code"]

        for year in range(start.year, end.year + 1):
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"

            # Запрашиваем весь год
            url = f"https://api.nbrb.by/exrates/rates/dynamics/{cur_id}?startDate={year_start}&endDate={year_end}"
            resp = requests.get(url)
            if resp.ok:
                try:
                    data = resp.json()
                    for entry in data:
                        result_rows.append({
                            "date": entry["Date"][:10],
                            "currency": name,
                            "code": cur_code,
                            "rate": entry["Cur_OfficialRate"]
                        })
                except Exception as ex:
                    return jsonify(error=f"Ошибка чтения данных для {name} ({year}): {str(ex)}"), 500
            else:
                return jsonify(error=f"Ошибка запроса к НБРБ для {name} ({year}): статус {resp.status_code}"), 502

            # Если год високосный, запрашиваем отдельно `YYYY-12-31`
            if is_leap_year(year):
                leap_date = f"{year}-12-31"
                url = f"https://api.nbrb.by/exrates/rates/{cur_id}?ondate={leap_date}"
                resp = requests.get(url)
                if resp.ok:
                    try:
                        data = resp.json()
                        result_rows.append({
                            "date": leap_date,
                            "currency": name,
                            "code": cur_code,
                            "rate": data["Cur_OfficialRate"]
                        })
                    except Exception as ex:
                        return jsonify(error=f"Ошибка чтения данных для {name} ({leap_date}): {str(ex)}"), 500
                else:
                    return jsonify(error=f"Ошибка запроса к НБРБ для {name} ({leap_date}): статус {resp.status_code}"), 502

    return jsonify(result_rows)



