from xml.etree import ElementTree
from bs4 import BeautifulSoup
import nltk
import json
import re
from newspaper import Article
sgm_path = 'C:/Users/dell/Desktop/package/ace_2005_td_v7/data/English/un/timex2norm/rec.games.chess.politics_20041217.2111.sgm'
with open(sgm_path, 'r') as f:
    data = f.read()
    # soup2 = BeautifulSoup(data, features="html.parser")
    # print(soup2)
    # print('-----------------------------------------------')

    soup = BeautifulSoup(data, features="lxml-xml")
    sgm_text = soup.text
    # print(soup)
    # print('-----------------------------------------------')
    print(sgm_text)
    print(sgm_text.find("the last two months since the move was decided upon"))

    # print(sgm_text.find("Fri, 5 Nov 2004 11:20:13 +1000"))
# with open('doc.txt','w') as f:
#     f.write(sgm_text)