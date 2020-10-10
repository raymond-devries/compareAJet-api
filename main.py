from fastapi import FastAPI
from pymongo import MongoClient, TEXT

app = FastAPI()

client = MongoClient('localhost', 27017)
db = client["testjet"]
jets_collection = db["jets"]


@app.on_event("startup")
def startup():
    jets_collection.create_index("name", unique=True)
    jets_collection.create_index("slug", unique=True)
    jets_collection.create_index([("name", TEXT)], default_language='english')


def search_jet_db(search_string):
    results = jets_collection.find({"$text": {"$search": search_string}},
                                   {"name": 1, "slug": 1, "_id": 0, "score": {"$meta": "textScore"}})
    results.sort([('score', {'$meta': 'textScore'})])
    return list(results)


@app.get("/jet/search/{jet_search_name}")
def search_jets(jet_search_string: str):
    return search_jet_db(jet_search_string)[:10]


def get_jet_db(jet_slug):
    return jets_collection.find_one({"slug": jet_slug}, {"_id": 0})


@app.get("/jet/{jet_slug}")
def get_single_jet(jet_slug: str):
    return get_jet_db(jet_slug)
