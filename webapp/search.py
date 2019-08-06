from flask import current_app


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
        index=index, 
        body={'query': {
                "bool": {
                    "should": [search_conditions]
                    }
                },
                'from': (page - 1) * per_page, 
                'size': per_page
              })
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
