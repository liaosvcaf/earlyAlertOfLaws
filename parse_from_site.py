import requests
import urllib.parse
import bs4
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}
base_url = 'http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml'
site_url = 'http://leginfo.legislature.ca.gov'

table_elems = {
        1: 'Law code',
        2: 'Subject',
        3: 'Author',
        4: 'Status'
}

bill_info_entries = ['Law code', 'Subject', 'Status']
pages_regex = re.compile('Page (\d+) of (\d+) pages')


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

def get_bills(soup):
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
    return bills

def get_bills_on_one_page(soup):
    bills = []
    results_table = soup.find('table')
    for row in results_table.tbody.findAll("tr", recursive=False):
        bill = dict()
        for i, td in enumerate(row.td.findAll("div", class_="commdataRow", recursive=False), 1):
            law_code_elem = td.a
            bill['Link'] = site_url + law_code_elem['href']
            law_code = law_code_elem.text
            law_code = law_code.replace('»', '').strip().replace(' ', '')
            bill['Law code'] = law_code
        bills.append(bill)
    return bills


def get_laws(keyword='', session_year='2019-2020', bill_number='', house='Both', law_code='All', statute_year='', chapter_number=''):
    '''
    Query bills from http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml
    session_year param must be in format '2019-2020' or '20192020'
    bill_number param must be in format 'AB-100' or 'AB100' or '100'
    Params: keyword, session_year, house, law_code, bill_number, statute_year, chapter_number
    
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
        bills = get_bills(soup)

    else:
        bills = []
        current_page = 1
        view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
        pages_num = int(pages_regex.search(bills_returned_pages.text).group(2))
        while current_page <= pages_num:
            paging_params = {
                    'dataNavForm:hidden_page_index': str(current_page),
                    'dataNavForm:go_to_page': str(current_page),
                    'javax.faces.ViewState': view_state
                    }
            paging_params = get_paging_params(paging_params, url_params)
            soup = get_soup_with_params(base_url, s, form=paging_params)
            bills_on_page = get_bills_on_one_page(soup)
            bills += bills_on_page
            #print(bills_on_page)
            view_state = soup.find('input', attrs={'id': 'j_id1:javax.faces.ViewState:3'})['value']
            current_page += 1
    return bills
