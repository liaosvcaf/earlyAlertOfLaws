from search import add_to_index, remove_from_index, make_query
from init_app import db
import traceback

db.Model.metadata.reflect(db.engine)

class SearchableMixin(object):
    @classmethod
    def get_monitoring_results(cls, query, page, per_page, time_limit=None):
        if not query:
            filtered = cls.query.order_by(Bill.last_action_date.desc()).all()
            filtered = filtered[(page - 1)*per_page:(page - 1)*per_page+per_page]
            total = len(filtered)
        else:
            ids, total = make_query(cls.__tablename__, query, page, per_page, time_limit)
            filtered = cls.query.filter(cls.id.in_(ids)).order_by(Bill.last_action_date.desc()).all()
        return filtered, total
    
    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query.all():
            try:
                print(obj.id)
                add_to_index(cls.__tablename__, obj)
            except:
                traceback.print_exc()
                continue
    

class Bill(SearchableMixin, db.Model):
    __searchable__ = ['title', 'subject', 'session', 'text', 'code', 
                      'authors', 'leginfo_id', 'last_action_date',
                      'date_published']
    __table__ = db.Model.metadata.tables['bills']
    
@classmethod
def reindex_by_leginfo_ids(cls, leginfo_ids):
    # sqlite doesn't allow very long queries
    # if we have a lot of ids in leginfo_ids and try to make query for all of
    # them at once, we'll get an error
    # so we query by parts
    
    # number of ids to query at once
    step = 20
    i = 0
    while i < len(leginfo_ids):
        ids_part = leginfo_ids[i:i+step]
        for obj in cls.query.filter(cls.leginfo_id.in_(ids_part)).all():
            add_to_index(cls.__tablename__, obj)
        i += step
      
@classmethod
def find_by_leginfo_id(cls, id):
    return cls.query.filter(cls.leginfo_id == id).first()
        
Bill.reindex_by_leginfo_ids = reindex_by_leginfo_ids
Bill.find_by_leginfo_id = find_by_leginfo_id

def get_all_keywords():
    with open('keywords.txt', 'r') as f:
        return [kw.strip() for kw in f.read().splitlines() if kw.strip() != '']

