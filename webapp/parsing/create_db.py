import re
from math import ceil
import sqlite3
import datetime
import traceback
import logging
from collections import namedtuple

import requests
import urllib.parse
import bs4
from html.parser import HTMLParser
from lxml import html
from elasticsearch import Elasticsearch

from .parsing_options import (db_file_name, table_name, elasticsearch_server_addr,
                             email_acc, email_pass, email_server, email_port)
from init_app import app
from models import Bill
from .notifications import get_auth_smtp_server, save_ids_of_changed_bills



class _HTMLToText(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._buf = []
        self.hide_output = False
    def handle_starttag(self, tag, attrs):
        if tag in ('p', 'br', 'h1', 'h2', 'h3', 'div') and not self.hide_output:
            self._buf.append('\n')
        elif tag in ('script', 'style'):
            self.hide_output = True
    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self._buf.append('\n')
    def handle_endtag(self, tag):
        if tag == 'p' or 'h' in tag:
            self._buf.append('\n')
        elif tag in ('script', 'style'):
            self.hide_output = False
    def handle_data(self, text):
        if text and not self.hide_output:
            self._buf.append(re.sub(r'\s+', ' ', text))
    def handle_charref(self, name):
        if not self.hide_output:
            n = int(name[1:], 16) if name.startswith('x') else int(name)
            self._buf.append(chr(n))
    def get_text(self):
        return re.sub(r' +', ' ', ''.join(self._buf))

def html_to_text(html):
    parser = _HTMLToText()
    try:
        parser.feed(html)
        parser.close()
        return parser.get_text().strip()
    except:
        raise
        return None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

    
# creating loggers

LOGGING_LEVEL = logging.DEBUG
LOG_FILE_NAME = "errors.log"
BILL_CHANGES_LOG_FILE_NAME = "bills.log"

logger = logging.getLogger("errors")
logger.setLevel(LOGGING_LEVEL)
handler = logging.FileHandler(LOG_FILE_NAME, 'a', 'utf-8')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

bills_changes_logger = logging.getLogger("bills_changes_logger")
bills_changes_logger.setLevel(LOGGING_LEVEL)
bills_changes_handler = logging.FileHandler(BILL_CHANGES_LOG_FILE_NAME, 'a', 'utf-8')
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
bills_changes_handler.setFormatter(formatter)
bills_changes_logger.addHandler(bills_changes_handler)

logger.info("PARSING STARTED")
bills_changes_logger.info("PARSING STARTED")

try:
    email_server = get_auth_smtp_server(email_server, email_port, email_acc, email_pass)
except:
    logger.error(traceback.format_exc())
    traceback.print_exc()

try:
    elasticsearch = Elasticsearch(elasticsearch_server_addr)
except:
    logger.error(traceback.format_exc())
    traceback.print_exc()


conn = sqlite3.connect(db_file_name)
conn.row_factory = dict_factory
cursor = conn.cursor()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}
base_url = 'http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml'
text_client_url = 'http://leginfo.legislature.ca.gov/faces/billTextClient.xhtml'
status_client_url = 'http://leginfo.legislature.ca.gov/faces/billStatusClient.xhtml'
site_url = 'http://leginfo.legislature.ca.gov'

bill_id_regex = re.compile('bill_id=([\dA-Za-z-]+)')
bill_code_regex = re.compile('[A-Z]+-\d+')
session_regex = re.compile('\(((20|19)\d{2}-(20|19)\d{2})\)')
date_publiched_regex = re.compile("(\d{2}/\d{2}/\d{4})")

date_reformat_regex = re.compile("(\d\d)/(\d\d)/(\d{2,4})")

table_elems = {
        1: 'Law code',
        2: 'Subject',
        3: 'Author',
        4: 'Status'
}

bill_info_entries = ['Law code', 'Subject', 'Status']
pages_regex = re.compile('Page (\d+) of (\d+) pages')

# constants of bill sctions types
BILL_UPDATED = 1
BILL_ADDED = 2

updated_bill_info = namedtuple('updated_bill_info', ['id', 'last_action_name'])


def log_exception(exc, bill_info):
    logger.error(bill_info["leginfo_id"] + ": " + exc)

def log_bill_changes(action, bill_info):
    if action == BILL_UPDATED:
        action_text = "Bill updated: "
    elif action == BILL_ADDED:
        action_text = "Bill added: "
    bills_changes_logger.info(action_text + bill_info["leginfo_id"])

def update_bills_in_elasticsearch(leginfo_ids):
    with app.app_context():
        Bill.reindex_by_leginfo_ids(leginfo_ids=leginfo_ids)

def update_bill(bill_dict):
    '''
    Inserts bill into db
    '''
    try:
        vals = "".join(['{0}="{1}",'.format(key, val) for key, val in bill_dict.items()])
        q = 'UPDATE {} SET {} WHERE leginfo_id="{}"'.format(table_name, vals[:-1], bill_dict['leginfo_id'])
        cursor.execute(q)
        conn.commit()
    except:
        logger.error(traceback.format_exc())
        traceback.print_exc()

def insert_bill_to_db(bill_dict, check_unique=False):
    '''
    Inserts bill into db
    '''
    try:
        columns = ', '.join(list(bill_dict.keys()))
        placeholders = ', '.join('?' * len(list(bill_dict.keys())))
        if check_unique:
            q = 'SELECT * FROM {} WHERE leginfo_id="{}"'.format(table_name, bill_dict['leginfo_id'])
            cursor.execute(q)
            found_bills = list(cursor)
            if found_bills:
                # don't insert if this bill is already in db
                return
        q = 'INSERT INTO {} ({}) VALUES ({})'.format(table_name, columns, placeholders)
        cursor.execute(q, tuple(bill_dict.values()))
        conn.commit()
    except:
        logger.error(traceback.format_exc())
        traceback.print_exc()

def get_bill_from_db_by_leginfo_id(leginfo_id):
    q = 'SELECT * FROM {} WHERE leginfo_id="{}"'.format(table_name, leginfo_id)
    cursor.execute(q)
    found_bills = list(cursor)
    if not found_bills:
        # empty list
        return None
    else:
        return found_bills[0]
            
def custom_tag_search(tag, span_id):
    if tag.has_key("id"):
        return (tag.name == "span" or  tag.name == "div") and tag["id"]==span_id
    return False

def get_bill_text_and_date_published(bill_info, text_client_url, bill_id_param, r_session):
    try:
        bill_text_url = text_client_url + '?' + bill_id_param
        bill_text_page = r_session.get(bill_text_url)
        
        tree = html.fromstring(bytes(bill_text_page.text, encoding='utf-8'))
        bill_text = tree.xpath("//div[@id='bill_all']")[0]
        
        for strike in bill_text.xpath("//strike"):
            strike.getparent().remove(strike)
        
        new_tree = html.tostring(bill_text)
        # [2:-1] - for removing b'' after converting bytes to str
        bill_info['text'] = re.sub(r'\n\n\n|\\t|\t|\\n', '', html_to_text(str(new_tree)))[2:-1]
    
        date_published = tree.xpath('//span[contains(text(), "Date Published")]')[0]
        date_publiched = date_publiched_regex.search(date_published.text).group(1)
        date_publiched = date_reformat_regex.sub(r'\3-\1-\2', date_publiched)
        bill_info['date_published'] = date_publiched
    except:
        log_exception(traceback.format_exc(), bill_info)
        traceback.print_exc()
        bill_info['text'] = ''
        bill_info['date_published'] = ''

def get_bill_attrs(bill_info, bill_status_soup):
    # title, house_location, authors
    # id on page - column in DB
    bill_attrs = {
            'statusTitle': 'title',
            'houseLoc': 'house_location',
            'leadAuthors': 'authors',
            }
    
    for span_id, db_col_name in bill_attrs.items():
        param = bill_status_soup.find(lambda tag: \
                                 custom_tag_search(tag, span_id))
        if param is not None:
            bill_info[db_col_name] = param.text.strip()
        else:
            bill_info[db_col_name] = ''

def get_bill_subject_code_session(bill_info, bill_status_soup):
    try:
        bill_title = bill_status_soup.find('div', id='bill_title').text
        bill_code = bill_code_regex.search(bill_title).group(0)
        session = session_regex.search(bill_title).group(1)
        bill_info['code'] = bill_code
        bill_info['session'] = session
    except Exception:
        log_exception(traceback.format_exc(), bill_info)
        traceback.print_exc()
        bill_info['code'] = ""
        bill_info['session'] = ""
        
    try:
        bill_subject = bill_title.replace(session, '').replace(bill_code, '').\
                       replace('()', '').strip()
        bill_info['subject'] = bill_subject
    except:
        log_exception(traceback.format_exc(), bill_info)
        traceback.print_exc()
        bill_info['subject'] = ''
        
    
def get_bill_last_action(bill_info, bill_status_soup):
    # get last action date and name
    try:
        last_action_date = bill_status_soup.find(lambda tag: \
                                 custom_tag_search(tag, "lastAction"))                
        if last_action_date is not None:
            last_action_date = last_action_date.text.strip()
            last_action_date = datetime.datetime.strptime(last_action_date, "%m/%d/%y").strftime("%Y-%m-%d")
            bill_info["last_action_date"] = last_action_date
        else:
            bill_info["last_action_date"] = ""
    except:
        bill_info["last_action_date"] = ""
        log_exception(traceback.format_exc(), bill_info)
        traceback.print_exc()
        
    try:
        last_action_name = bill_status_soup.find("label", attrs={"for": "lastAction"}) 
        if last_action_name is not None:
            bill_info["last_action_name"] = last_action_name.text.replace(":", "")
        else:
            bill_info["last_action_name"] = ""
    except:
        bill_info["last_action_name"] = ""
        log_exception(traceback.format_exc(), bill_info)
        traceback.print_exc()

def save_bills_info(bill_links, r_session, check_unique):
    '''
    Parses bills from links, gets bills' attributes and calls function 
    which inserts bill info to db (inserting happens after 
    getting info for one bill)
    bill_links - links to bills
    r_session - request.Session object
    check_unique - check if bill is already in db, don't add if it is
    '''
    saved_bills_leginfo_ids = []
    updated_bills_ids = []
    added_bills_ids = []
    bills_info = list()
    for bill_link in bill_links:
        # get leginfo site bill id
        bill_info = dict()
        bill_id_parsed = bill_id_regex.search(bill_link)
        try:
            bill_id_param = bill_id_parsed.group(0)
            bill_info['leginfo_id'] = bill_id_parsed.group(1)
        except:
            print("Failed to parse bill id from URL: ", bill_link)
            continue
        
        # get bill attributes
        bill_status_url = status_client_url + '?' + bill_id_param
        
        # if error getting the page, retry
        got_response = False
        attempt = 0
        while not got_response and attempt < 5:
            try:
                bill_page = r_session.get(bill_status_url)
                bill_status_soup = bs4.BeautifulSoup(bill_page.text, 'html.parser')
                if bill_status_soup.find("div", id="bill_status") is not None:
                    got_response = True
            except:
                log_exception(traceback.format_exc(), bill_info)
                traceback.print_exc()
                attempt += 1
        if not got_response:
            continue
            
        get_bill_last_action(bill_info, bill_status_soup)

        db_bill = get_bill_from_db_by_leginfo_id(bill_info['leginfo_id'])

        if db_bill is not None:
            if bill_info["last_action_date"] == db_bill["last_action_date"]:
                # no changes
                continue
        
        get_bill_attrs(bill_info, bill_status_soup)
        get_bill_subject_code_session(bill_info, bill_status_soup)
        get_bill_text_and_date_published(bill_info, text_client_url, bill_id_param, r_session)
        
        bills_info.append(bill_info)
        print("Bill changed: ",  bill_info["code"])
        try:
            if db_bill is not None:
                # bill exists, update
                update_bill(bill_info)
                log_bill_changes(BILL_UPDATED, bill_info)
                updated_bill_info_ = updated_bill_info(id=bill_info["leginfo_id"],
                                                       last_action_name=\
                                                       db_bill['last_action_name'])
                updated_bills_ids.append(updated_bill_info_)
            else:
                # add new bill
                insert_bill_to_db(bill_info, check_unique=check_unique)
                log_bill_changes(BILL_ADDED, bill_info)
                added_bills_ids.append(bill_info["leginfo_id"])
            saved_bills_leginfo_ids.append(bill_info["leginfo_id"])
        except:
            log_exception(traceback.format_exc(), bill_info)
            traceback.print_exc()
            continue
    update_bills_in_elasticsearch(saved_bills_leginfo_ids)
    print("Updated bills: ", updated_bills_ids)
    print("Added bills: ", added_bills_ids)
    bills_changes_logger.info("Updated bills: " + ", ".join([bill.id for bill in updated_bills_ids]))
    bills_changes_logger.info("Added bills: " + ", ".join(added_bills_ids))
    save_ids_of_changed_bills(added_bills_ids, updated_bills_ids)
    return bills_info

def get_soup_with_params(base_url, session, params_dict=None, form=None):
    if params_dict:
        url = base_url + '?' + urllib.parse.urlencode(params_dict)
    else:
        url = base_url
    if form:
        r = session.post(url, headers=headers, data=form)
    else:
        r = session.get(url, headers=headers)
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    return soup
    
def get_paging_params(d, old_params):
    new_dict = dict()
    new_dict['dataNavForm'] = 'dataNavForm'
    new_dict['dataNavForm:hidden_keyword'] = old_params['keyword']
    new_dict['dataNavForm:hidden_sess_yr'] = old_params['session_year']
    new_dict['dataNavForm:hidden_bill_nbr'] = old_params['bill_number']
    new_dict['dataNavForm:hidden_house'] = old_params['house']
    new_dict['dataNavForm:hidden_author'] = 'All'
    new_dict['dataNavForm:hidden_nextTen'] = 'NextTen'
    new_dict.update(d)
    return new_dict

def get_bills(soup, num=10):
    bills = []
    results_table = soup.find('table', id='bill_results')
    for row in results_table.tbody.findAll("tr", recursive=False):
        link_elem = row.find("a", recursive=True)
        bills.append(site_url + link_elem['href'])
        if num != -1 and len(bills) > num:
            break
    return bills

def get_bills_on_one_page(soup):
    bills = []
    results_table = soup.find('table')
    for row in results_table.tbody.findAll("tr", recursive=False):
        link_elem = row.td.find("div", class_="commdataRow", recursive=False)
        bills.append(site_url + link_elem.a['href'])
    return bills

def parse_laws_into_db(num=-1, keyword='', session='2019-2020', bill_number='', house='Both', law_code='All', statute_year='', chapter_number='', check_unique=False):
    '''
    Query bills from http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml
    Parse and add to database
    session param must be in format '2019-2020' or '20192020'
    bill_number param must be in format 'AB-100' or 'AB100' or '100'
    Params: keyword, session_year, house, law_code, bill_number, statute_year, chapter_number
    num - number of bills to return. -1 if all available bills
    check_unique - check if bill is already in db, don't add if it is
    '''    

    session = session.replace('-', '')
    bill_number = bill_number.replace('-', '')

    url_params = {
            'house': house,
            'session_year': str(session),
            'lawCode': law_code,
            'keyword': keyword,
            'bill_number': bill_number,
            'author': 'All',
            'chapterYear': str(statute_year),
            'chapterNumber': str(chapter_number),
            }
    
    s = requests.Session()
    soup = get_soup_with_params(base_url, s, params_dict=url_params)
    
    bills_returned_pages = soup.find('div', id='text_bill_returned')
    
    if not bills_returned_pages:
        # only one page with all laws
        bills_found = False
        attempts = 0
        bills_on_page_links = None
        while not bills_found and attempts < 5:
            try:
                bills_on_page_links = get_bills(soup, num)
                bills_found = True
            except:
                attempts += 1
        if not bills_on_page_links:
            return None
        save_bills_info(bills_on_page_links, s, check_unique)
    else:
        current_page = 1
        view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
        
        all_pages_num = int(pages_regex.search(bills_returned_pages.text).group(2))
        # always 10 laws on one page
        all_laws_num = all_pages_num*10
        if num > all_laws_num or num == -1:
            num = all_laws_num
        pages_num = ceil(num/10)
        while current_page <= pages_num:            
            paging_params = {
                    'dataNavForm:hidden_page_index': str(current_page),
                    'dataNavForm:go_to_page': str(current_page),
                    'javax.faces.ViewState': view_state
                    }
            paging_params = get_paging_params(paging_params, url_params)
            soup = get_soup_with_params(base_url, s, form=paging_params)
            bills_on_page_links = get_bills_on_one_page(soup)
            save_bills_info(bills_on_page_links, s, check_unique)
            try:
                view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
            except:
                traceback.print_exc()
            current_page += 1
        cursor.close()


'''
Usage examples:

Save all bills (every session) from site to database 
'''

'''
year = 2020
while year >= 2000:
    prev_year = year - 1
    session = str(prev_year) + '-' + str(year)
    parse_laws_into_db(session=session, num=-1)
    year -= 2
'''
'''
clear_bills_changes()

year = 2018
while year >= 2000:
    prev_year = year - 1
    session = str(prev_year) + '-' + str(year)
    parse_laws_into_db(session=session, num=-1)
    year -= 2

send_email_notifications(email_server, email_acc)


parse_laws_into_db(session="2020-2018", num=-1)
send_email_notifications(email_server, sender_email=email_acc)
'''