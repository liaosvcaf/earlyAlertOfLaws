from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from search import add_to_index, remove_from_index, query_index
from init_app import db, app
from flask import current_app

db.Model.metadata.reflect(db.engine)
'''
engine = create_engine('sqlite:///db_some.db', convert_unicode=True, echo=False)
Base = declarative_base()
Base.metadata.reflect(engine)

db_session = scoped_session(sessionmaker(bind=engine))
'''

class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0).all(), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        #print(cls.query.filter(cls.id.in_(ids)))
        return cls.query.filter(cls.id.in_(ids)).all(), total
    
    '''
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total
    '''

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
            add_to_index(cls.__tablename__, obj)


class Bill(SearchableMixin, db.Model):
    __searchable__ = ['title', 'subject', 'session']
    __table__ = db.Model.metadata.tables['education_bills']
 

def create_index(index_name='bill'):
    es_object = current_app.elasticsearch
    created = False
    # index settings
    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "members": {
                "dynamic": "strict",
                "properties": {
                    "title": {
                        "type": "text"
                    },
                    "session": {
                        "type": "text"
                    }
                }
            }
        }
    }
    try:
        if not es_object.indices.exists(index_name):
            # Ignore 400 means to ignore "Index Already Exist" error.
            es_object.indices.create(index=index_name, ignore=400, body=settings)
            print('Created Index')
            created = True
    except Exception as ex:
        print(str(ex))
    finally:
        return created

if __name__ == '__main__':
    with app.app_context():
        #create_index()
        #Bill.reindex()
        bills, total = Bill.search('Education')
        print(len([b.title + '\n' for b in bills]))
        print(total)
        

    '''
    from sqlalchemy.orm import scoped_session, sessionmaker
    db_session = scoped_session(sessionmaker(bind=engine))
    for item in db_session.query(Bill.id, Bill.title):
        print(item)
    '''