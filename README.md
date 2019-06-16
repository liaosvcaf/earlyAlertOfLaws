# earlyAlertOfLaws
A web service for monitoring new laws in California

There are thousands of new laws being introduced each year in California. These laws have profound impact on citizens’ daily life if passed. SVCAF is especially interested in keeping track of the ones related to Asian, Chinese, education issues so we can timely alert the Chinese American community to engage the legislation process.  However, it is extremely hard for any single person to keep track of them or monitor them due to the large number of laws being proposed every year.  

As a result, we are developing a web-based service to automatically monitor the new laws of California. 
* A configurable web interface for users to define a few keywords
* A backend process to use the data & APIs from https://openstates.org/ to search CA laws to find the ones matching the keywords
* The backend process automatically refresh daily to get latest results
* A web page (it could be the same page accepting keywords configuration) displaces the query results with links for the laws matched.
* Preferred scripting language is Python
* Deploy this service within www.svcaf.org , a wordpress-based site hosted on an AWS machine. 
