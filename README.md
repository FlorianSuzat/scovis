SCOVIS
=======

__*Scores Visualisation*__

---

Documentation
-------------
This projet is a prototype to have SCOOPS visualisation datatable outside GWS django framework.
Still in development...

1. place SCOOPS like «instant» json in datas/«xpname» directory
2. each «instant» file should be named YYYYMMDDHH_TT.json where YYYYMMDDHH is the forecast network, TT the term of the forecast
3. create «score» with 
<code>python3 scripts/aggregate.py -r datas/«XPREF» -t datas/«XPTEST»</code>
this will create a file called XPTESTvsXPREF.json file in scores directory
4. open scovis.html in your web browser
5. fill the form at the top with a score file : for example scores/XPTESTvsXPREF.jso
6. view your score card



License
-------

This software is governed by the open-source [CeCILL-C](http://www.cecill.info) license under French law, cf. LICENSE.txt.
Downloading and using this code means that you have had knowledge of the CeCILL-C license and that you accept its terms. 
You can find it in licence directory
