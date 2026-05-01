from flask import Flask, request, Response
import requests
import os
from simpleeval import simple_eval

app = Flask(__name__)

def formatResponse(value):
    accept = request.headers.get("Accept", "")
 
    wants_xml = (
        "application/xml" in accept or "text/xml" in accept
    ) and "application/json" not in accept
 
    if wants_xml:
        body = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><result>{value}</result>"
        return Response(body, mimetype="application/xml")
 
    # Default: JSON. The spec says the JSON value should be the number itself.
    return Response(str(value), mimetype="application/json")
 
 
def undefinedResponse():
    return formatResponse("undefined")

def getAirportTemp(iata: str):
    # Get coordinates of airport first based on IATA
    info = requests.get(
        "https://airport-data.com/api/ap_info.json",
        params={"iata": iata},
        timeout=10,
    ).json()

    # airport data returns 200 for unknown airports
    if info.get("icao") is None or info.get("location") is None:
        return None
 
    lat = info.get("latitude")
    lon = info.get("longitude")
    if lat is None or lon is None:
        return None
 
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
        },
        timeout=10,
    ).json()
 
    return weather.get("current_weather", {}).get("temperature")
 
 
def getStockPrice(stock: str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock}"
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    ).json()

    result = resp.get("chart", {}).get("result")
    if not result:
        return None
    return result[0].get("meta", {}).get("regularMarketPrice")
 

@app.route('/', methods=['GET'])
def handle():
    queryAirportTemp = request.args.get('queryAirportTemp')
    queryStockPrice = request.args.get('queryStockPrice')
    queryEval = request.args.get('queryEval')

    # Return undefined if no query or more than one query 
    queries = [queryAirportTemp, queryStockPrice, queryEval]
    if sum(q is not None for q in queries) != 1:
        return undefinedResponse()
    
    try:
        if queryAirportTemp is not None:
            value = getAirportTemp(queryAirportTemp.strip().upper())
        elif queryStockPrice is not None:
            value = getStockPrice(queryStockPrice.strip().upper())
        else:
            value = simple_eval(queryEval)
    except Exception:
        return undefinedResponse()
    
    if value is None:
        return undefinedResponse()
    
    return formatResponse(value)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))