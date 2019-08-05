from init_app import app
from models import Bill

if __name__ == '__main__':
    with app.app_context():
        Bill.reindex()