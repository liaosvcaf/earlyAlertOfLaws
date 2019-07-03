import requests
import urllib.parse
import bs4
import sqlite3
import re
from math import ceil


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db = 'new.db'
conn = sqlite3.connect(db)
conn.row_factory = dict_factory
cursor = conn.cursor()
columns_names = ['code', 'subject', 'title', 'house_location', 'last_amendment_date', 'authors', 'session', 'leginfo_id']
placeholders = ', '.join('?' * len(columns_names))

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}
base_url = 'http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml'
text_client_url = 'http://leginfo.legislature.ca.gov/faces/billTextClient.xhtml'
status_client_url = 'http://leginfo.legislature.ca.gov/faces/billStatusClient.xhtml'
site_url = 'http://leginfo.legislature.ca.gov'

bill_id_regex = re.compile('bill_id=([\dA-Za-z-]+)')
bill_code_regex = re.compile('[A-Z]+-\d+')
session_regex = re.compile('\(((20|19)\d{2}-(20|19)\d{2})\)')

table_elems = {
        1: 'Law code',
        2: 'Subject',
        3: 'Author',
        4: 'Status'
}

bill_info_entries = ['Law code', 'Subject', 'Status']
pages_regex = re.compile('Page (\d+) of (\d+) pages')


def update_keywords(bill_links, keyword, table='bills'):
    for bill_link in bill_links:
        leginfo_id = bill_id_regex.search(bill_link).group(1)
        q = f'SELECT * FROM education_bills WHERE leginfo_id LIKE "%{leginfo_id}%"'
        cursor.execute(q)
        row = list(cursor)[0]
        keywords = row['keywords']
        keywords += ' ' + keyword
        q = 'UPDATE education_bills SET keywords="' + keywords + f'" WHERE leginfo_id="{leginfo_id}"'
        cursor.execute(q)

def insert_bills_to_db(bills):
    table_name = 'bills'
    for bill_dict in bills:
        columns = ', '.join(list(bill_dict.keys()))
        q = 'INSERT INTO {} ({}) VALUES ({})'.format(table_name, columns, placeholders)
        cursor.execute(q, tuple(bill_dict.values()))
    conn.commit()

def get_bills_info(bill_links, r_session):
    bills_info = list()
    for bill_link in bill_links:
        bill_info = dict()
        bill_id_parsed = bill_id_regex.search(bill_link)
        bill_id_param = bill_id_parsed.group(0)
        bill_info['leginfo_id'] = bill_id_parsed.group(1)
        
        bill_status_url = status_client_url + '?' + bill_id_param
        bill_page = r_session.get(bill_status_url)

        bill_status_soup = bs4.BeautifulSoup(bill_page.text, 'html.parser')
        
        try:
            bill_title = bill_status_soup.find('div', id='bill_title').text
            bill_code = bill_code_regex.search(bill_title).group(0)
            session = session_regex.search(bill_title).group(0)
            bill_info['code'] = bill_code
            bill_info['session'] = session
        except Exception as e:
            with open('r.html', 'w', encoding='utf-8') as f:
                f.write(bill_page.text)
            print()
            print(e)
            print(bill_link)
            print()
            continue
        
        try:
            bill_subject = bill_title.replace(session, '').replace(bill_code, '').strip()
            bill_info['subject'] = bill_subject
        except:
            bill_info['subject'] = ''
        
        
        # id on page - column in DB
        bill_attrs = {
                'statusTitle': 'title',
                'houseLoc': 'house_location',
                'leadAuthors': 'authors',
                'lastAction': 'last_amendment_date'
                }
        
        for span_id, db_col_name in bill_attrs.items():
            try:
                bill_info[db_col_name] = bill_status_soup.find('span', id=span_id).text.strip()
            except:
                bill_info[db_col_name] = ''
        
        bills_info.append(bill_info)
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

def parse_laws_into_db(num=-1, keyword='', session='2019-2020', bill_number='', house='Both', law_code='All', statute_year='', chapter_number=''):
    '''
    Query bills from http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml
    Parse and add to database
    session param must be in format '2019-2020' or '20192020'
    bill_number param must be in format 'AB-100' or 'AB100' or '100'
    Params: keyword, session_year, house, law_code, bill_number, statute_year, chapter_number
    num - number of bills to return. -1 if all available bills
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
        bills_on_page_links = get_bills(soup, num)
        print(bills_on_page_links)
        bills_info = get_bills_info(bills_on_page_links, s)
        insert_bills_to_db(bills_info, keyword)
        print(bills_info)
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
            bills_info = get_bills_info(bills_on_page_links, s)
            insert_bills_to_db(bills_info, keyword)
            #print(bills_info)
            print(current_page)
            try:
                view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
            except:
                print('!!!!!!!!!111', current_page)
            current_page += 1
        cursor.close()



'''
Usage examples:

Save all bills (every session) from site to database 
year = 2020
while year >= 2000:
    prev_year = year - 1
    session = str(prev_year) + '-' + str(year)
    parse_laws_into_db(session=session, num=-1)
    year -= 1
'''
