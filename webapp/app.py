from forms import AddKeywordForm, SubscribeEmailForm, TimeWindowForm
from flask import flash, render_template, request, escape, redirect, url_for, session
from flask_paginate import Pagination, get_page_parameter

from parsing.notifications import send_email_subs_start_notification
from parsing.parsing_options import (email_server, email_acc, email_port, 
                                     email_pass)
from init_app import app
from models import Bill


def get_all_keywords():
    with open('keywords.txt', 'r') as f:
        return [kw.strip() for kw in f.read().splitlines() if kw.strip()]

def subscribe_email(email, kws, time_limit):
    with open('subscribed_emails.txt', 'a') as f:
        f.write("\n" + email + ":" + kws + ":" + time_limit + "\n")

def unsubscribe_email(email):
    with open('subscribed_emails.txt', 'r') as f:
        lines = [line.split(":") for line in f.read().splitlines()]
        lines_updated = [":".join(line) for line in lines if line[0] != email]
    with open('subscribed_emails.txt', 'w') as f:      
        f.write("\n".join(lines_updated))
        

@app.route('/')
def redirect_main_page():
    return redirect(url_for('search', search='all'))

@app.route('/search/<search>', methods=['GET', 'POST'])
def search(search):
    # time window in years
    time_window = "1y"
    session_tw = session.get("time_window", None)
    if session_tw:
        time_window = session_tw
    if request.method == 'POST':
        time_window = request.form.get("window") + "y"
        session["time_window"] = time_window
    per_page = 10
    page = request.args.get(get_page_parameter(), type=int, default=1)
    offset = (page - 1) * per_page
    
    if search == 'all':
        query = get_all_keywords()
    else:
        query = [search]
            
    bills, total = Bill.get_monitoring_results(query, page=page, 
                                               per_page=per_page,
                                               time_limit = time_window)
    pagination = Pagination(page=page, total=total, per_page=per_page,
                            offset=offset,
                            css_framework='bootstrap4')
    form_tw = TimeWindowForm()
    return render_template('results.html', 
                           results=bills,
                           per_page=per_page,
                           page=page,
                           pagination=pagination,
                           escape=escape,
                           form_tw=form_tw)

@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    if request.method == 'POST':
        if request.form.get("action_type") == "add":
            new_keyword = request.form.get('new_kw')
            try:
                with open('keywords.txt', 'a') as f:
                    f.write('\n' + new_keyword + '\n')
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

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        email = request.form.get('email')
        kws = request.form.get('kws')
        kws = [kw.strip() for kw in kws.split(",")]
        time_limit = request.form.get('time_limit')
        try:
            subscribe_email(email, ",".join(kws), time_limit)
            send_email_subs_start_notification(email, kws, email_server, 
                                               email_acc, email_port, email_pass)
        except Exception as e:
            flash(f'Error: ' + str(e))
        else:
            flash(f'Subscription successsful')
    form = SubscribeEmailForm(request.form)
    return render_template('subscribe.html', form=form)
        
@app.route('/unsubscribe/<email>')
def unsubscribe(email):
    try:
        unsubscribe_email(email)
        flash(f'Unubscribed successsful')
    except Exception as e:
        flash(f'Error: ' + str(e))
    return render_template('unsubscribe.html')

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
    #app.run()
    app.run("0.0.0.0", port=80)
