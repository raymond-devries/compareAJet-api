from fastapi import FastAPI, Query
from pymongo import MongoClient, TEXT
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional, List

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


@app.get("/jet/search/")
def search_jets(jet_search_name: str):
    return search_jet_db(jet_search_name)


def get_jet_db(jet_slug: str):
    return jets_collection.find_one({"slug": jet_slug}, {"_id": 0})


def get_multiple_jets_db(jet_slugs: list):
    return list(jets_collection.find({"slug": {"$in": jet_slugs}}, {"_id": 0}))


@app.get("/jet/{jet_slug}")
def get_single_jet(jet_slug: str):
    return get_jet_db(jet_slug)


def chart_data(jet_data: list, labels: list):
    numeric_data = [{k: v for (k, v) in item.items() if isinstance(v, (int, float))} for item in jet_data]
    labels = []
    [labels.extend(numeric_data_keys.keys()) for numeric_data_keys in numeric_data]
    labels = list(set(labels))
    chart_data = {"labels": labels, "datasets": []}
    for number_data in numeric_data:
        data = []
        for label in labels:
            try:
                data.append(number_data[label])
            except KeyError:
                data.append(0)

        chart_data["datasets"].append({"data": data})

    return chart_data


@app.get("/jet/charts/", )
def get_jet_charts(jet_slugs: Optional[List[str]] = Query(None)):
    jet_data = get_multiple_jets_db(jet_slugs)
    return {"names": [data["name"] for data in jet_data],
            "radar_chart": chart_data(jet_data)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
