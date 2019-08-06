from flask import current_app


def remove_all_index(index):
    current_app.elasticsearch.indices.delete(index=index, ignore=[400, 404])

from init_app import app
with app.app_context():
    remove_all_index("bills")