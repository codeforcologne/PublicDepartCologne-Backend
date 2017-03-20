import flask
import unicodedata
import gzip
import urllib.request
from bs4 import BeautifulSoup
from io import StringIO
import psycopg2
import geojson
import configparser
import json

app = flask.Flask(__name__)


def getdata(code, limit):
    data_url = "http://www.kvb-koeln.de/generated/?aktion=show&code=" + str(code) + "&title=graph"
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
                      'Safari/537.36 '
    }
    req = urllib.request.Request(data_url, None, headers)
    page = urllib.request.urlopen(req)
    gzipped = page.info().get('Content-Encoding') == 'gzip'

    if gzipped:
        buf = StringIO(page.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = page

    """
        headers = requests.utils.default_headers()

        headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
                              'Safari/537.36',
            }
        )

        request = requests.get(data_url, headers=headers)

        c = request.text

        print(request.headers)

        with open("htmldata.html", 'w') as f:
            f.write(request.text)


        with open("htmldata.html", 'rb') as f:
            c = f.read().decode("UTF-8")
    """
    soup = BeautifulSoup(data, "html.parser")

    table = soup.findAll("table")[1]

    # print(table)

    data = []

    for row in table.findAll("tr"):
        # print(row)
        item = {}
        cols = row.findAll("td")
        if len(cols) >= 3:
            item['id'] = str(unicodedata.normalize('NFKD', cols[0].getText())).strip()
            item['haltestelle'] = str(unicodedata.normalize('NFKD', cols[1].getText())).replace(" ", "")
            item['abfahrt'] = str(unicodedata.normalize('NFKD', cols[2].getText())).strip().replace(" Min", "")
            data.append(item)

    if limit is not None:
        return data[0:int(limit)]
    else:
        return data


def shutdown_server():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


@app.before_request
def option_autoreply():
    if flask.request.method == 'OPTIONS':
        resp = app.make_default_options_response()

        headers = None
        if 'ACCESS_CONTROL_REQUEST_HEADERS' in flask.request.headers:
            headers = flask.request.headers['ACCESS_CONTROL_REQUEST_HEADERS']

        h = resp.headers

        # Allow the origin which made the XHR
        h['Access-Control-Allow-Origin'] = flask.request.headers['Origin']
        # Allow the actual method
        h['Access-Control-Allow-Methods'] = flask.request.headers['Access-Control-Request-Method']
        # Allow for 10 seconds
        h['Access-Control-Max-Age'] = "10"

        # We also keep current headers
        if headers is not None:
            h['Access-Control-Allow-Headers'] = headers

        return resp


@app.after_request
def set_allow_origin(resp):
    h = resp.headers

    # Allow crossdomain for other HTTP Verbs
    if flask.request.method != 'OPTIONS' and 'Origin' in flask.request.headers:
        h['Access-Control-Allow-Origin'] = flask.request.headers['Origin']

    return resp


@app.route("/")
def home():
    req = flask.request
    return flask.render_template("index.html", path=flask.request.path, base=flask.request.base_url,
                                 title="PublicDepartCologne")


@app.route('/database', methods=['GET'])
def database():
    lat = flask.request.args.get('lat', default=None)
    long = flask.request.args.get('long', default=None)
    # radius = flask.request.args.get('radius', default=None)

    if lat is None or long is None:
        return flask.render_template("error.html", error_title="No Lat or long",
                                     error="Bitte gib die Parameter ?lat und &long an")
    else:
        # print("Test")
        try:
            config = configparser.ConfigParser()
            config.read("config.ini")
            host = config.get("postgres", "host")
            db = config.get("postgres", "db")
            user = config.get("postgres", "user")
            password = config.get("postgres", "password")
            key = config.get("graphhopper","key")


            connect_str = "dbname=" + db + " user=" + user + " host=" + host + " " + \
                          "password=" + password + ""
            # use our connection values to establish a connection
            conn = psycopg2.connect(connect_str)
            # create a psycopg2 cursor that can execute queries
            cursor = conn.cursor()

            # ST_Distance(haltestellen.geom, ST_MakePoint(""" + lat + """, """ + long + """)::geography) as distance

            cursor.execute((
                               """SELECT *, ST_Distance(haltestellen.geom, ST_MakePoint(<long>, <lat>)::geography) as distance, st_asgeojson(geom) FROM public.haltestellen ORDER BY distance LIMIT 5; """).replace(
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
            
            start_geo=lat + "%2C" + long            
            
            for col in rows:
                finish_geo=col[12][0] + "%2C" + col[12][1]
                url="https://graphhopper.com/api/1/route?point=" + start_geo + "&point=" + finish_geo + "&vehicle=foot&instructions=false"+"&points_encoded=false&calc_points=false&locale=de&key=" + key
                req = urllib.request.Request(url)
                page = urllib.request.urlopen(req)
                routing_json=json.load(page)    
                rows.append(routing_json["paths"][0]["distance"])
                rows.append(routing_json["paths"][0]["time"]/1000/60)
            # print(rows)
            # print(rows[0][0])
            for col in rows:
                # print(col)
                properties = {}

                # print(col)

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
                properties['foot_distance'] = col [13]
                properties['foot_time'] = col[14]

                geo = col[12]
                # properties['geo'] = the_tuple[8]

                feature = geojson.Feature(geometry=geojson.loads(geo), properties=properties)
                # print(properties)
                features.append(feature)

            collection = geojson.FeatureCollection(features)
            # return flask.jsonify(data)
            resp = flask.Response(geojson.dumps(collection), status=200, mimetype='application/json')
            return resp
            # return flask.jsonify(data)

        except psycopg2.DatabaseError as e:
            print("Uh oh, can't connect. Invalid dbname, user or password?")
            print(e)
        return ""


@app.route("/abfahrt/<code>", methods=['GET', 'POST'])
@app.route("/abfahrt/")
def api(code=None):
    limit = flask.request.args.get('limit', default=None)
    if code is None:
        return flask.render_template("error.html", base=flask.request.base_url, path=flask.request.path,
                                     error="Bitte nutze <code>{{ base }}&lt;code&gt;/</code> um die Abfahrtszeiten zu bekommen",
                                     error_title="Error: Kein Code")
    else:
        req = flask.request

        data = getdata(code, limit)
        resp = flask.Response(data, status=200, mimetype='application/json')
        return flask.jsonify(data)


@app.route("/shutdown", methods=['GET'])
def shutdown():
    shutdown_server()
    return 'Server shutting down'


if __name__ == "__main__":
    # For Public use
    # app.run(host='192.168.199.142')
    app.run()
