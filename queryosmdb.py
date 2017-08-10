#
#  queryosmdb.py
#  
#  Copyright 2017 Fabio Mazza
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
import json
import sqlite3
import requests
stoptable = "fermate"
print("Richiedo le fermate del bus...")
r=requests.post("http://overpass-api.de/api/interpreter", """
[out:json];area[\"name\"=\"Torino\"][\"boundary\"=\"administrative\"][\"admin_level\"=\"8\"];
node[\"highway\"=\"bus_stop\"](area);out body;""")

conn =  sqlite3.connect("bustoOSM.db")
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS "+stoptable)
c.execute("CREATE TABLE "+stoptable+" (id INTEGER PRIMARY KEY,  lat REAL, lon REAL, ref INTEGER, name TEXT);")
#fstop=open("fermateOSM.json")
#stopsjson = json.load(fstop)
stopsjson = r.json()
dateExecuted = stopsjson["osm3s"]["timestamp_areas_base"]
fermate = stopsjson["elements"]
#fstop.close()
print("Fermate ricevute")
del r
print("Richiedo le fermate del tram...")
r=requests.post("http://overpass-api.de/api/interpreter", """
[out:json];area[\"name\"=\"Torino\"][\"boundary\"=\"administrative\"][\"admin_level\"=\"8\"];
node[\"railway\"=\"tram_stop\"](area);out body;""")
fermateTram = r.json()["elements"]
fermate.extend(fermateTram)
#ftramstop.close()
print("Fermate ricevute")
del fermateTram
del r
print("Richiedo le linee...")
r=requests.post("http://overpass-api.de/api/interpreter", """
[out:json];area["name"="Torino"]["boundary"="administrative"]["admin_level"="8"];
relation["network"="Formula"](area);out meta;""")
lineeElem = r.json()["elements"]
print("Linee ricevute")
del r
print("Costruisco il db")
fermateout = []
stessefermate = 0
numerofermate = 0
for stop in fermate:
    id = stop["id"]
    tags = stop["tags"]
    if "ref" in tags and tags["ref"].isdigit():
        #print(str(stop["id"])+"\t"+tags["name"]+"\t ref: "+tags["ref"]+"\n")
        fem={"id": stop["id"], "lat":stop["lat"],"lon": stop["lon"], "ref": int(tags["ref"]), "name": tags["name"]}
        t =tuple(fem.values())
        try:
            c.execute("INSERT INTO "+stoptable+" VALUES (?,?,?,?,?)", t)
            fermateout.append(fem)
            numerofermate+=1
        except sqlite3.IntegrityError:
            stessefermate+=1

#c.executemany("INSERT INTO "+stoptable+" VALUES (?,?,?,?,?)", valori)
#print(valori)
print("Trovate "+str(numerofermate)+" fermate")
print("e "+str(stessefermate)+" fermate identiche")
conn.commit()
del fermate
#cerco le linee
numerolinee = 0
lineeout = []
#flinee = open("lineeGTT.json")

for linea in lineeElem:
    #Devo prendere le fermate coorrispondenti alle linee
    tags = linea["tags"]
    timestamp  = linea["timestamp"]
    direction = tags["direction"]
    numero = tags["ref"]
    fermate = []
    #print("Linea numero: "+ str(numero))
    for element in linea["members"]:
        if element["role"]=="stop":
            c = conn.cursor()
            c.execute("SELECT ref from "+stoptable+" WHERE id="+str(element["ref"]))
            arr=c.fetchall()
            #t=c.fetchone();
            if len(arr)!=0:
                fermate.append(arr[0][0])
    if(len(fermate)!=0):
        linea={"lastModified": timestamp, "direction": direction,"numero":numero, "stops": fermate}
        if "from" in tags:
            linea["from"]=tags["from"]
        lineeout.append(linea)
        numerolinee +=1
print("Trovate "+str(numerolinee)+" linee")
conn.close()
print("Creo il file json...")
out={"queryDate":dateExecuted,"fermate":fermateout, "linee": lineeout}
#print(out)
fout = open("osmdata.json", 'w')
json.dump(out,fout,sort_keys=True, indent=4)
fout.close()
print("Ho creato il file osmdata.json")
