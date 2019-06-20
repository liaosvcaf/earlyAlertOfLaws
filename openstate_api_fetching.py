import requests


def get_laws(date='2019-01-01', num=40):
    '''
    Function for fetching California laws from OpenState API
    Params:
    date: date of introduction (default 2019-01-01)
    num: number of laws to return (default 40)
    '''
    q = '''
    {
      search_1: bills(first: %(num)s, jurisdiction: "California", actionSince: "%(date)s") {
        edges {
          node {
            id
            identifier
            title
            classification
            updatedAt
            createdAt
            legislativeSession {
              identifier
              jurisdiction {
                name
              }
            }
            actions {
              date
              description
              classification
            }
            documents {
              date
              note
              links {
                url
              }
            }
            versions {
              date
              note
              links {
                url
              }
            }
    
            sources {
              url
              note
    
            }
          }
        }
      }
    }
    ''' % {'num': num, 'date': date}
    
    params = {'query': q}
    
    headers = {'X-API-KEY': '126d56c7-e0ac-42c2-8d72-2b23b5bc81ef'}
    url = 'https://openstates.org/graphql?'
    r = requests.post(url, params=params, headers=headers)
    return r.text

print(get_laws())
