from flask import current_app


def remove_index(index_name='bill'):
    current_app.elasticsearch.indices.delete(index=index_name, ignore=[400, 404])

def create_index(index_name='bill'):
    created = False
    # index settings
    settings = {
      "mappings": {
        "properties": {
          "last_action_date": {
            "type": "date",
            "ignore_malformed": True
          }
        }
      }
    }
    try:
        if not current_app.elasticsearch.indices.exists(index_name):
            # Ignore 400 means to ignore "Index Already Exist" error.
            current_app.elasticsearch.indices.create(index=index_name, ignore=400, body=settings)
            print('Created Index')
        created = True
    except Exception as ex:
        print(str(ex))
    finally:
        return created

def add_to_index(index, model):
    if not current_app.elasticsearch:
        print("not current_app.elasticsearch")
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id,
                                    body=payload)

def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)
    
def make_query(index, query_params, page, per_page, time_limit="1y", returned_val="id"):
    # returned_val - str "id" (id from DB and elasticsearch) or "leginfo_id"
    if not current_app.elasticsearch:
        return [], 0
    
    search_field = ['title', 'subject', 'text']
    
    search_conditions = [{'fuzzy': {field: {"value": query_param, "fuzziness": "auto"}}} for field in search_field 
                         for query_param in query_params]
    time_lim_q = "now-" + str(time_limit)
    search = current_app.elasticsearch.search(
        index = index, 
        body ={'query': {
                'bool': {
                    "minimum_should_match": "1",
                    'should': [search_conditions],
                    "filter" : [
                      { "range" : { "date_published" : { "gte" : time_lim_q}}}
                    ]
                },
              },
              'from': (page - 1) * per_page, 
              'size': per_page,
              'sort': [{
                 'last_action_date': {
                    'order': 'desc'
                     }
                 }]
               })
    vals = []
    if returned_val == "id":
        vals = [int(hit['_id']) for hit in search['hits']['hits']]
    elif returned_val == "leginfo_id":
        vals = [hit['_source']["leginfo_id"] for hit in search['hits']['hits']]
    return vals, search['hits']['total']['value']

"""
from init_app import app

with app.app_context():
    print(make_query("bill", ["chinese"], 1, 10, time_limit="1y"))
"""