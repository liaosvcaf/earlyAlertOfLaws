import requests
import json
from itertools import chain


def get_laws(num=4, action_since='2019-01-01', 
             updated_since='2019-01-01', chamber='', included_attrs=None):
    '''
    Function for fetching California laws from OpenState API
    Params:    
    num: 
    Number of laws to return
    
    chamber
    Limit to bills originating in a given chamber. 
    (e.g. upper, lower, legislature)
    
    updated_since
    Limit to bills that have had data updated since a given time.
    Time should be in the format YYYY-MM-DD[THH:MM:SS].

    action_since
    Limit to bills that have had actions since a given time.
    Time should be in the format YYYY-MM-DD.

    included_attrs
    bill attributes to return 
    (see https://docs.openstates.org/en/latest/api/v2/types.html#billnode )

    '''
    if num == -1:
        num = 1000000000
    
    # default values
    if not included_attrs:
        included_attrs=['id', 'identifier', 'classification', 'title', 
                        'subject', 'createdAt', 'updatedAt']
        
    all_edges = []
    cursor = ''
    
    hasNextPage = True
    
    while hasNextPage and num > 0:
        num_div = num // 100
        print(num_div)
        num_mod = num % 100
        if num_div == 0:
            cur_num = num_mod
        else:
            cur_num = 100
        print(cur_num)
        q = '''
        {
          bills(first: %(cur_num)s, jurisdiction: "California", chamber: "%(chamber)s"
          actionSince: "%(action_since)s", updatedSince: "%(updated_since)s", after: "%(cursor)s") {
            edges {
              node {
                %(attrs)s
              }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
          }
        }
        ''' % {'cur_num': cur_num, 'updated_since': updated_since, 
               'action_since': action_since, 'chamber': chamber,
               'cursor': cursor, 'attrs':'\n'.join(included_attrs)}
        
        num -= 100
        
        params = {'query': q}
        
        headers = {'X-API-KEY': '126d56c7-e0ac-42c2-8d72-2b23b5bc81ef'}
        url = 'https://openstates.org/graphql?'
        r = requests.post(url, params=params, headers=headers)
        r_dict = json.loads(r.text)['data']['bills']
        edges = r_dict['edges']
        all_edges += edges
        hasNextPage = bool(r_dict['pageInfo']['hasNextPage'])
        cursor = r_dict['pageInfo']['endCursor']
    return all_edges

laws = get_laws(included_attrs=['subject'])
subjects = [law['node']['subject'] for law in laws]
subjects = list(chain(*subjects))
print(subjects)

