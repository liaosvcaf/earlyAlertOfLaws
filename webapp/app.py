from forms import SimpleSearchForm, AdvancedSearchForm
from flask import Flask, flash, render_template, request, redirect, url_for
from init_app import app
from models import Bill
from flask_paginate import Pagination, get_page_parameter


@app.route('/', methods=['GET', 'POST'])
def simple_search():
    search = SimpleSearchForm(request.form)
    if request.method == 'POST':
        print((url_for('search_results', form=search, query=search.data)))
        redirect((url_for('search_results', form=search, query=search.data)))
        #return search_results(search)
    return render_template('simple_search.html', form=search)
 
@app.route('/search_results')
def search_results():
    search_string = request.args.get('search')
    print('search_string', search_string)
    
    per_page = 10
    page = request.args.get(get_page_parameter(), type=int, default=1)
    print('!!!', page)
    offset = (page - 1) * per_page
    
    bills, total = Bill.search(search_string, page=page, per_page=per_page)

    if not bills:
        flash('No results found!')
        return redirect('/')
    else:
        search = False
        q = request.args.get('q')
        if q:
            search = True
        
        print(total)
        pagination = Pagination(page=page, total=total, per_page=per_page,
                                offset=offset,
                                css_framework='bootstrap4')
        return render_template('results.html', 
                               results=bills,
                               per_page=per_page,
                               page=page,
                               pagination=pagination) 

@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    search = AdvancedSearchForm(request.form)
    if request.method == 'POST':
        print((url_for('search_results', form=search, query=search.data)))
        redirect((url_for('search_results', form=search, query=search.data)))
        #return search_results(search)
    return render_template('advanced_search.html', form=search)
    
@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    pass
    
@app.route('/links', methods=['GET', 'POST'])
def links():
    pass

if __name__ == '__main__':
    app.run()
