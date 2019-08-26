from search import remove_index, create_index

from init_app import app
with app.app_context():
    remove_index("bill")
    create_index()