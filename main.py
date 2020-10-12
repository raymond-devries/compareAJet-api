from fastapi import FastAPI, Query
from pymongo import MongoClient, TEXT
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional, List
from random import randrange

app = FastAPI()

example = ("boeing-f-a-18e-f-super-hornet", "lockheed-f-94-f-97-starfire")

client = MongoClient('localhost', 27017)
db = client["testjet"]
jets_collection = db["jets"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    jets_collection.create_index("name", unique=True)
    jets_collection.create_index("slug", unique=True)
    jets_collection.create_index([("name", TEXT)], default_language='english')


def search_jet_db(search_string):
    results = jets_collection.find({"$text": {"$search": search_string}},
                                   {"name": 1, "slug": 1, "_id": 0, "score": {"$meta": "textScore"}})
    results.sort([('score', {'$meta': 'textScore'})])
    if results is None:
        return []
    return list(results)


def get_random_jet_db():
    jet = list(jets_collection.aggregate([{"$sample": {"size": 1}}, {"$project": {"_id": 0, "name": 1, "slug": 1}}]))[0]
    return jet


@app.get("/jet/search/")
def search_jets(jet_search_name: str):
    return search_jet_db(jet_search_name)


@app.get("/jet/random/")
def get_random_jet():
    return get_random_jet_db()


def get_jet_db(jet_slug: str):
    return jets_collection.find_one({"slug": jet_slug}, {"_id": 0})


def get_multiple_jets_db(jet_slugs: list):
    return list(jets_collection.find({"slug": {"$in": jet_slugs}}, {"_id": 0}))


@app.get("/jet/{jet_slug}")
def get_single_jet(jet_slug: str):
    return get_jet_db(jet_slug)


def get_rgb_colors():
    return [randrange(125, 250) for _ in range(3)]


def radar_chart_data(jet_data: list, labels: list):
    chart_data = {"labels": labels, "datasets": []}
    for number_data in jet_data:
        data = []
        for label in labels:
            try:
                data.append(number_data[label])
            except KeyError:
                data.append(0)

        rgb = get_rgb_colors()
        chart_data["datasets"].append({"data": data, "label": number_data["name"],
                                       "backgroundColor": f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.2)",
                                       "borderColor": f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.8)"})

    return chart_data


def bar_chart_data(jet_data: list, field: str):
    label = []
    data = []
    for item in jet_data:
        label.append(item["name"])
        try:
            data.append(item[field])
        except KeyError:
            data.append(0)

    rgb = get_rgb_colors()
    return {"labels": label, "datasets": [{"data": data, "label": field,
                                           "backgroundColor": f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.5)",
                                           "borderColor": f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.8)"
                                           }]}


RADAR_CHART1 = ["Empty weight", "Gross weight", "Service ceiling"]
RADAR_CHART2 = ["Length", "Wingspan", "Height"]
BAR_CHARTS = ["Maximum speed", "Wing area", "number created"]

USED_KEYS = RADAR_CHART1 + RADAR_CHART2 + BAR_CHARTS


@app.get("/jet/charts/", )
def get_jet_charts(jet_slugs: Optional[List[str]] = Query(None)):
    jet_data = get_multiple_jets_db(jet_slugs)
    chart_data = {"names": [data["name"] for data in jet_data],
                  "radar_chart1": radar_chart_data(jet_data, RADAR_CHART1),
                  "radar_chart2": radar_chart_data(jet_data, RADAR_CHART2),
                  "bar_charts": {item + "bar chart": bar_chart_data(jet_data, item) for item in BAR_CHARTS}}
    for jet in jet_data:
        for key in USED_KEYS:
            try:
                del jet[key]
            except KeyError:
                pass
    chart_data["other_data"] = jet_data
    return chart_data


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
