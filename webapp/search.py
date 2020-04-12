from flask import current_app
import traceback


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
          },
          "text": {
            "type": "text",
            "normalizer": "useLowercase",
          },
        }
      },
        "analysis": {
          "normalizer": {
            "useLowercase": {
              "type": "custom",
              "filter": [ "lowercase" ]
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
    try:
        if not current_app.elasticsearch:
            print("not current_app.elasticsearch")
            return
        payload = {}
        for field in model.__searchable__:
            payload[field] = getattr(model, field)
            if payload[field] == "" and field == "date_published":
                payload[field] = None
            if field == "text":
                payload[field] = payload[field].lower()
        current_app.elasticsearch.index(index=index, id=model.id,
                                        body=payload)
    except:
        traceback.print_exc()

def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)
    
def make_query(index, query_params, page, per_page, time_limit="1y", returned_val="id"):
    # returned_val - str "id" (id from DB and elasticsearch) or "leginfo_id"
    if not current_app.elasticsearch:
        return [], 0
    
    search_field = ['title', 'subject', 'text']
    
    search_conditions = []
    
    '''
    # simple (only one word)
    search_conditions = [{'fuzzy': {field: {"value": query_param, "fuzziness": "0"}}} for field in search_field 
                         for query_param in query_params]
    
    # multi-word exact match (adjacent and order kept)
    for param in query_params:
        if len(param.split(" ")) > 1:
            conditions = [{'match_phrase': {field: param}} for field in search_field]
            must = [{'bool': {"minimum_should_match": "1", 'should': conditions}}]
            search_condition = {'bool': {'must': must}}
            search_conditions.append(search_condition)
        else:
            for field in search_field:
                search_condition = {'fuzzy': {field: {"value": param, "fuzziness": "0"}}}
                search_conditions.append(search_condition)
    '''
    
    # multi-word fuzzy (words not necessary abjacent)
    for param in query_params:
        if len(param.split(" ")) > 1:
            shoulds = []
            for term in param.split(" "):
                conditions = [{'fuzzy': {field: {"value": term, "fuzziness": "0"}}} for field in search_field]
                shoulds.append(conditions)
            must = [{'bool': {"minimum_should_match": "1", 'should': should}} for should in shoulds]
            search_condition = {'bool': {'must': must}}
            search_conditions.append(search_condition)
        else:
            for field in search_field:
                search_condition = {'fuzzy': {field: {"value": param, "fuzziness": "0"}}}
                search_conditions.append(search_condition)
                
    print(search_conditions)
    
    time_lim_q = "now-" + str(time_limit)
    search = current_app.elasticsearch.search(
        index = index, 
        body ={'query': {
                'bool': {
                    "minimum_should_match": "1",
                    'should': [search_conditions],
                    "filter" : [
                      { "range" : { "last_action_date" : { "gte" : time_lim_q}}}
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