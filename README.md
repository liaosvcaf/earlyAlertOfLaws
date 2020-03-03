# earlyAlertOfLaws
A web service for monitoring new laws in California

There are thousands of new laws being introduced each year in California. These laws have profound impact on citizens’ daily life if passed. SVCAF is especially interested in keeping track of the ones related to Asian, Chinese, education issues so we can timely alert the Chinese American community to engage the legislation process.  However, it is extremely hard for any single person to keep track of them or monitor them due to the large number of laws being proposed every year.  

As a result, we are developing a web-based service to automatically monitor the new laws of California, with the following features: 
* A configurable web interface for users to define a few keywords, such as education, asian, chinese, etc.
* A backend process to use the data http://leginfo.legislature.ca.gov to search CA laws to find the ones matching the keywords
  * Scripting language is Python
  * links to the matched laws are returned with additional info. such as abstract and full content, etc.
  * The backend process automatically refreshes daily to get latest results
* A web page (it could be the same page accepting keywords configuration) displaces the query results with links for the laws matched.
* Deploy this service within www.svcaf.org , a wordpress-based site hosted on an AWS machine.
  * set up both testing and production deployment, triggered automatically.

# Deployment

Current live website: http://54.180.108.54/search/all

## General requirements

At least 2 GB of RAM is required to run ElasticSearch.

Exposed 80 (HTTP) port is required to access app on other machines.

## Instruction
The following instruction is for Ubuntu.  However, you can deploy on another OS (tested on Windows and CentOS). Adapt steps 1 and 2 to your OS

1. Install Python and pip
  ```
  sudo apt-get update
  sudo apt-get install python3.6
  sudo apt-get -y install python3-pip
  ```

2. Install ElasticSearch

    Official guides for various OS:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/install-elasticsearch.html

    1. Install Java:

    `sudo apt-get install default-jdk -y`

    2. Import the Elasticsearch PGP Key

    `wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -`

    3. Installing from the APT repository

    ```
    sudo apt-get install apt-transport-https
    echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list
    sudo apt-get update && sudo apt-get install elasticsearch -y
    ```

    4. Start elasticsearch service
    Use the update-rc.d command to configure Elasticsearch to start automatically when the system boots up:

    `sudo update-rc.d elasticsearch defaults 95 10`

    Elasticsearch can be started and stopped using the service command:

    ```
    sudo -i service elasticsearch start
    sudo -i service elasticsearch stop
    ```

    You can check service status with

    `sudo service elasticsearch status -l`
    
    Press q to quite the status screen
    
    Logs most likely are in
    /var/log/elasticsearch/

4. Install Python requirements  
   `git@github.com:svcaf/earlyAlertOfLaws.git`
   
   `cd earlyAlertOfLaws/webapp`

    `pip3 install -r requirements.txt`

5. Create elasticsearch index

    Go to directory with scripts and run 
    
    `python3 recreate_index.py`

6. Add bills from db to elasticsearch  

    Go to directory with scripts and run 
    
    `python3 reindex.py`

This step may take a long time. The resulting bills.db (SQLite format) file is big;
```
ls -l bills.db
-rw-rw-r-- 1 ubuntu ubuntu 197,799,936 Mar  1 01:06 bills.db
```

7. Run the app  

    `sudo python3 app.py`
    
    Sudo is required to to use port 80

## Stopping app
If you use Ctrl-C or close terminal/ssh session, app will stop. To keep it running, use linux utility screen. To stop the app use `sudo fuser -k 80/tcp`

## DB updating
To update the db regularly, schedule script update_db.py (use linux cron or windows scheduler). This script is also sends email notifications after updating

For example, update the DB every Sunday 0:0
```
0 0 * * 0 /usr/bin/python3 /home/ubuntu/california_bills_app/update_db.py >> ~/cron.log 2>&1
```

## Recreate elasticsearch data
If there are problems with elasticsearch data, you can delete and create bills entries with:

* recreate_index.py - remove "bills" index from elasticsearch (remove all bills) and create index again 
* reindex.py - create "bills" index (uses bills from db to create index)
* parse.py - starts procedures for updating db (via site parsing) and sending email notifications after it


## Options

Options for app (elastic search address, database filename) are in init_app.py

Options for parsing and email notifications (email account and server to send notifications from) are in parsing/parsing_options.py
