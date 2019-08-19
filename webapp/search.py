from flask import current_app


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
    
def make_query(index, query_params, page, per_page):
    if not current_app.elasticsearch:
        return [], 0
    
    search_field = ['title', 'subject', 'text']
    
    search_conditions = [{'fuzzy': {field: query_param}} for field in search_field 
                         for query_param in query_params]
    
    search = current_app.elasticsearch.search(
        index = index, 
        body ={'query': {
                'bool': {
                    'should': [search_conditions]
                    }
              },
              'from': (page - 1) * per_page, 
              'size': per_page,
              'sort': [{
                 'last_action_date': {
                    'order': 'desc'
                     }
               }]
               })
    print([bill['_source'].get('last_action_date', None) for bill in search['hits']['hits']])
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    print(ids)
    return ids, search['hits']['total']['value']
