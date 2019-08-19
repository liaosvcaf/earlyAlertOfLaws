from forms import AddKeywordForm
from flask import flash, render_template, request, escape, redirect, url_for
from init_app import app
from models import Bill
from flask_paginate import Pagination, get_page_parameter


def get_all_keywords():
    with open('keywords.txt', 'r') as f:
        return [kw.strip() for kw in f.read().splitlines() if kw.strip() != '']
    

@app.route('/')
def redirect_main_page():
    return redirect(url_for('results', search='all'))

@app.route('/<search>')
def results(search):
    per_page = 10
    page = request.args.get(get_page_parameter(), type=int, default=1)
    offset = (page - 1) * per_page
    
    if search == 'all':
        query = get_all_keywords()
    else:
        query = [search]
        
    bills, total = Bill.get_monitoring_results(query, 
                                               page=page, per_page=per_page)
    pagination = Pagination(page=page, total=total, per_page=per_page,
                            offset=offset,
                            css_framework='bootstrap4')
    return render_template('results.html', 
                           results=bills,
                           per_page=per_page,
                           page=page,
                           pagination=pagination,
                           escape=escape)

@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    if request.method == 'POST':
        if request.form.get("action_type") == "add":
            new_keyword = request.form.get('new_kw')
            try:
                with open('keywords.txt', 'a') as f:
                    f.write(new_keyword + '\n')
                    flash(f'New keyword {new_keyword} added')
            except Exception as e:
                    flash(f'Error adding new keyword: ' + str(e))
        elif request.form.get("action_type") == "delete":
            kw_to_delete = request.form.get('name')
            try:
                kws = get_all_keywords()
                new_kws_list = list(filter(lambda kw: kw != kw_to_delete, kws))
                with open('keywords.txt', 'w') as f:
                    f.write('\n'.join(new_kws_list))
            except Exception as e:
                flash("Error deletuing keyword: " + str(e))
                kws = []
    #add_new_kw_form = AddKeywordForm(request.form)
    add_new_kw_form = AddKeywordForm()
    try:
        kws = get_all_keywords()
    except Exception as e:
        flash("Error getting keywords: " + str(e))
        kws = []
    return render_template('keywords.html', keywords=kws, form_add=add_new_kw_form)

@app.route('/links', methods=['GET'])
def links():
    try:
        with open('links.txt', 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            links = [line.split(',') for line in lines]
    except:
        links = []
    
    return render_template('links.html', links=links)

@app.route('/bills/<bill_id>')
def bill_info(bill_id):
    bill = Bill.query.filter(Bill.id==bill_id).first()
    return render_template('bill_page.html', bill=bill)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run()
    #app.run("0.0.0.0", port=80)
