import psycopg2
import json
import geojson

try:

    lat = "6.9881160312996728"
    long = "50.96659064159747"
    radius = "100"

    connect_str = "dbname='hackcity' user='postgres' host='localhost' " + \
                  "password='Super3!'"
    # use our connection values to establish a connection
    conn = psycopg2.connect(connect_str)
    # create a psycopg2 cursor that can execute queries
    cursor = conn.cursor()

    # ST_Distance(haltestellen.geom, ST_MakePoint(""" + lat + """, """ + long + """)::geography) as distance

    cursor.execute((
                       """SELECT *, ST_Distance(haltestellen.geom, ST_MakePoint(<lat>, <long>)::geography) as distance, st_asgeojson(geom) FROM public.haltestellen WHERE ST_DWithin(haltestellen.geom, ST_MakePoint(<lat>, <long>)::geography, """ + radius + """);""").replace(
        "<lat>", lat).replace("<long>", long))
    # cursor.execute("""SELECT * FROM public.haltestellen WHERE ST_DWithin(haltestellen.geom, ST_MakePoint(6.9881160312996728, 50.96659064159747)::geography, 10000);""")
    # create a new table with a single column called "name"
    # cursor.execute("""CREATE TABLE tutorials (name char(40));""")
    # run a SELECT statement - no data in there, but we can try it
    # cursor.execute("""SELECT * from tutorials""")
    rows = cursor.fetchall()
    # print(rows)
    # print(sum(rows, ()))
    features = []

    #print(rows)
    #print(rows[0][0])
    for col in rows:
        #print(col)
        properties = {}

        print(col)


        # print("Sum " + sum(the_tuple, ()))
        # print(the_tuple.split(",")[1:len(the_tuple)-1])
        """
        print(type(the_tuple))
        print(the_tuple)
        print(tuple(the_tuple))
        """

        distance = col[1]

        properties['gid'] = col[0]
        properties['name'] = col[1]
        properties['knotennummer'] = str(col[2])
        properties['typ'] = col[3]
        properties['nr_stadtteil'] = str(col[4])
        properties['stadtteil'] = col[5]
        properties['nr_stadtbez'] = col[6]
        properties['stadtbez'] = col[7]
        properties['hyperlink'] = col[8]
        properties['distance'] = col[11]

        geo = col[12]
        # properties['geo'] = the_tuple[8]

        feature = geojson.Feature(geometry=geojson.loads(geo), properties=properties)
        print(properties)
        features.append(feature)

    collection = geojson.FeatureCollection(features)
    print(geojson.dumps(collection))
    # return flask.jsonify(data)

except psycopg2.DatabaseError as e:
    print("Uh oh, can't connect. Invalid dbname, user or password?")
    print(e)
