import requests
import urllib.parse
import bs4
import sqlite3
import re
from math import ceil


db = 'db.db'
conn = sqlite3.connect(db)
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

def insert_bills_to_db(bills, keyword=''):
    if not keyword:
        table_name = 'all_bills'
    else:
        table_name = keyword + '_bills'
    for bill_dict in bills:
        columns = ', '.join(list(bill_dict.keys()))
        q = 'INSERT INTO {} ({}) VALUES ({})'.format(table_name, columns, placeholders)
        cursor.execute(q, tuple(bill_dict.values()))
    conn.commit()
    cursor.close()

def get_bills_info(bill_links, r_session):
    bills_info = list()
    for bill_link in bill_links:
        bill_info = dict()
        print(bill_link)
        bill_id_parsed = bill_id_regex.search(bill_link)
        bill_id_param = bill_id_parsed.group(0)
        bill_info['leginfo_id'] = bill_id_parsed.group(1)
        
        bill_status_url = status_client_url + '?' + bill_id_param
        bill_page = r_session.get(bill_status_url)
        bill_status_soup = bs4.BeautifulSoup(bill_page.text, 'html.parser')
        
        bill_title = bill_status_soup.find('div', id='bill_title').text
        bill_code = bill_code_regex.search(bill_title).group(0)
        session = session_regex.search(bill_title).group(0)
        bill_subject = bill_title.replace(session, '').replace(bill_code, '').strip()
        bill_info['code'] = bill_code
        bill_info['session'] = session
        bill_info['subject'] = bill_subject
        
        # id on page - column in DB
        bill_attrs = {
                'statusTitle': 'title',
                'houseLoc': 'house_location',
                'leadAuthors': 'authors',
                'lastAction': 'last_amendment_date'
                }
        
        for span_id, db_col_name in bill_attrs.items():
            try:
                bill_info[db_col_name] = bill_status_soup.find('span', id=span_id).text
            except:
                bill_info[db_col_name] = ''
        '''
        bill_title_row = bill_status_soup.find('span', id=).text
        house_loc = bill_status_soup.find('span', id='houseLoc').text
        last_amendment_date = bill_status_soup.find('span', id='lastAction').text
        authors = bill_status_soup.find('span', id='leadAuthors').text
        bill_info['title'] = bill_title_row
        bill_info['house_location'] = house_loc
        bill_info['last_amendment_date'] = last_amendment_date
        bill_info['authors'] = authors
        '''
        
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
    with open('r.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
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
        bill = dict()
        for i, td in enumerate(row.findAll("td", recursive=False), 1):
            if type(td) != str and type(td) != bs4.element.NavigableString:
                text = td.text
            else:
                text = str(td)
            table_elem = table_elems[i]
            if table_elem == 'Law code':
                bill['Link'] = site_url + td.a['href']
            if text == 'x' and table_elem == 'Subject':
                text = None
            if table_elem in bill_info_entries:
                bill[table_elem] = text.strip()
        bills.append(bill)
        if len(bills) > num:
            break
    return bills

def get_bills_on_one_page(soup):
    bills = []
    results_table = soup.find('table')
    for row in results_table.tbody.findAll("tr", recursive=False):
        link_elem = row.td.find("div", class_="commdataRow", recursive=False)
        bills.append(site_url + link_elem.a['href'])
    return bills


def parse_laws_into_db(num=10, keyword='', session_year='2019-2020', bill_number='', house='Both', law_code='All', statute_year='', chapter_number=''):
    '''
    Query bills from http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml
    Parse and add to database
    session_year param must be in format '2019-2020' or '20192020'
    bill_number param must be in format 'AB-100' or 'AB100' or '100'
    Params: keyword, session_year, house, law_code, bill_number, statute_year, chapter_number
    num - number of bills to return. -1 if all available bills
    '''    

    session_year = session_year.replace('-', '')
    bill_number = bill_number.replace('-', '')

    url_params = {
            'house': house,
            'session_year': str(session_year),
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
        bills = get_bills(soup, num)
    else:
        bills = []
        current_page = 1
        view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
        
        all_pages_num = int(pages_regex.search(bills_returned_pages.text).group(2))
        # always 10 laws on one page
        all_laws_num = all_pages_num*10
        if num > all_laws_num or num == -1:
            num = all_laws_num
        pages_num = ceil(num/10)
        while current_page <= pages_num:
            print('!11')
            
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
            bills += bills_info
            #print(bills_on_page)
            view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
            current_page += 1
    bills = bills[0:num]
    return bills

parse_laws_into_db(num=10, keyword='education')

