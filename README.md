# **Non-contact opitcal thermometries for emissive semiconductor material**
Python programs designed for controling multiple instruments to automatically measure the temperature of semiconductor material using optical approaches. This repository includes two appraoches for materials with different optical properties. Both appraoches have high spatical resolution (sub um) and high temperature sensitivity (sub K). 

## 1. Pump-probe luminescence thermometry (PPLT):
This appraoch is mainly based on temperature dependent emission spectrum.This approach is widely used for measuring temperature change during solid phase optical refrigeration. More theory and technical detail can be found in https://aip.scitation.org/doi/abs/10.1063/1.4811759. 

#### 2. Creating a db file that contains two tables: "school" and "people_scopus".
* "school" table includes school rank, school name, affilation id  and searching status.
* "people_scopus" table includes fullname, first name, last name, people id, given name and surname saved in scopus database, affilation rank, affilation id, affilation name, number of papers published, number of citation, H-index and searching status.

#### 3. Creating a json file that contains papers published by each faculty in each department, which includes affilation name, number of citation, paper id, author id, published year, published journal name.

#### 4. Calculating several publication statistics for each department and save to a text file in "result" folder.

## **Prerequisites**
* A Scopus API key, which can be found in https://dev.elsevier.com/
* A network connection inside a Scopus or ScienceDirect subscribeing institution
* Python 3.x. Extra python packages required can be found in requiremnt.txt     


## **Issues**
* There is search limition for each Scopus API key. If all publication information is requred for 101 departments, one API key won't be enough.   
* For certain faculties, data format save in scopus database is not correct. There will be errors when searching publication inforamtion on scopus by author ID. To avoild this error, substitue "site-packages/elsapy/utils.py" in python with "utils.py" file in this repository.
