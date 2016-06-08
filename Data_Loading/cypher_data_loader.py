
import sys, getopt
import py2neo as neo4j
import json
import datetime
import math
import time

epoch = datetime.datetime.utcfromtimestamp(0)

def readargs(argv):
    
    inputfile=''
    password=''
    remoteserver=''
    maxsize=600000
    batchsize=1000
    partition_key='election'
    constraints=False
    partitionsize=0
    startval=0
    
    try:
        opts, args = getopt.getopt(argv,"hi:p:r:m:b:k:z:s:c")
    except getopt.GetoptError:
        print 'neo2.py -i <inputfile> -p <password for local server> -r <remote server url> \
        -m <maxnumberrows> -b <batchsize> -k <partition_key> -s <startval>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'neo2.py -i <inputfile> -p <password for local server> -r <remote server url> \
            -m <maxnumberrows> -b <batchsize> -k <partition_key> -s <startval>'
            sys.exit()
        elif opt == "-i":
            inputfile = arg
        elif opt == "-p":
            password = arg
        elif opt == "-r":
            remoteserver = arg
        elif opt == "-m":
            maxsize = int(arg)
        elif opt == "-b":
            batchsize = int(arg)
        elif opt == "-k":
            partition_key = arg
        elif opt == "-c":
            constraints = True
        elif opt == "-z":
            partitionsize = arg
        elif opt == "-s":
            startval=int(arg)
            
    return inputfile, password, remoteserver, maxsize, batchsize, partition_key, constraints, partitionsize, startval

def authenticate(password, remoteserver):
    mode='none'
    try:
        if ((password=='') and (remoteserver=='')):
            mode='no auth'
            graph = neo4j.Graph()
            return graph

        elif (remoteserver==''):
            mode='password local'
            pyn.authenticate("localhost:7474","neo4j",password)
            graph = neo4j.Graph()
            return graph

        elif (remoteserver!=''):
            mode='remote server'
            remote_graph = neo4j.Graph(remoteserver)
            return remote_graph

    except:
        print 'neo2.py problem with authentication for mode ' + mode
        sys.exit(2)
    
    return
   
def unix_time_millis(dt):
    return int( (dt - epoch).total_seconds() * 1000.0)

def addtweet(data,databatch):
    
    pretweet=''
    
    if (('retweeted' in data) and ('retweeted_status' in data)):
        pretweet = data['retweeted_status'];

    elif (('quoted_status' in data)):
        pretweet = data['quoted_status'];
        
    if (pretweet != ''):
        databatch['tweets'].append(pretweet) 
    
    databatch['tweets'].append(data)

#create roughly hourly partition
def getPartition(timestamp_ms):
    return int(timestamp_ms / (3600 * 1000)) # divide milliseconds to get hours

def dropConstraints(graph):
    
    constraints = [
        "DROP CONSTRAINT ON (t:Tweet) ASSERT t.id_str IS UNIQUE;",
        "DROP CONSTRAINT ON (u:User) ASSERT u.screen_name IS UNIQUE;",
        "DROP CONSTRAINT ON (h:Hashtag) ASSERT h.name IS UNIQUE;",
        "DROP CONSTRAINT ON (l:Link) ASSERT l.url IS UNIQUE;",
        "DROP CONSTRAINT ON (s:Source) ASSERT s.source IS UNIQUE;",
        "DROP CONSTRAINT ON (p:Place) ASSERT p.id IS UNIQUE;",
        "DROP CONSTRAINT ON (t:Tweet) ASSERT t.id IS UNIQUE;",
        "DROP CONSTRAINT ON (t:Tweet) ASSERT t.partition_key IS UNIQUE;",
        "DROP CONSTRAINT ON (u:User) ASSERT u.partition_key IS UNIQUE;",
        "DROP CONSTRAINT ON (h:Hashtag) ASSERT h.partition_key IS UNIQUE;",
        "DROP CONSTRAINT ON (l:Link) ASSERT l.partition_key IS UNIQUE;",
        "DROP CONSTRAINT ON (s:Source) ASSERT s.partition_key IS UNIQUE;",
        "DROP CONSTRAINT ON (p:Place) ASSERT p.partition_key IS UNIQUE;"
    ]
    for constraint in constraints:
        try:
            graph.cypher.execute(constraint)
            print constraint
        except Exception as e:
            print 'Could not drop the following constraint -- ', constraint

def setConstraints(graph, partition_key):
    constraints = [
        """CREATE CONSTRAINT ON (t:Tweet_{0}) ASSERT t.id_str IS UNIQUE;""".format(partition_key),
        """CREATE CONSTRAINT ON (u:User_{0}) ASSERT u.screen_name IS UNIQUE;""".format(partition_key),
        """CREATE CONSTRAINT ON (h:Hashtag_{0}) ASSERT h.name IS UNIQUE;""".format(partition_key),
        """CREATE CONSTRAINT ON (l:Link_{0}) ASSERT l.url IS UNIQUE;""".format(partition_key),
        """CREATE CONSTRAINT ON (s:Source_{0}) ASSERT s.source IS UNIQUE;""".format(partition_key),
        """CREATE CONSTRAINT ON (p:Place_{0}) ASSERT p.id IS UNIQUE;""".format(partition_key),
        """CREATE INDEX ON :Tweet_{0}(timestamp_int);""".format(partition_key)
    ]
    for constraint in constraints:
        try:
            graph.cypher.execute(constraint)
            print constraint
        except Exception as e:
            print 'Could not create the following constraint -- ', constraint


def tweetQuery(partition_key):
    
    tweetstr = """MERGE (tweet:Tweet_{0}:Tweet {{id_str:t.id_str}})
        ON CREATE SET tweet.text = t.text,
            tweet.created_at = t.created_at,
            tweet.favorite_count = t.favorite_count,
            tweet.timestamp_int = toInt(t.timestamp_ms)
        ON MATCH SET tweet += {{
            favorite_count:t.favorite_count
        }}
        FOREACH (coord IN [c IN [t.coordinates] WHERE c IS NOT NULL] |
            SET tweet.coordinates = coord.coordinates
        )""".format(partition_key)
#     print 'tweet', tweetstr
    return tweetstr

def userQuery(partition_key):
    
    userstr = """
        MERGE (user:User_{0}:User {{screen_name:u.screen_name}})
        ON CREATE SET user.name = u.name,
            user.location = u.location,
            user.followers = u.followers_count,
            user.description = u.description,
            user.following = u.friends_count,
            user.time_zone = u.time_zone,
            user.statuses_count = u.statuses_count,
            user.verified = u.verified
        ON MATCH SET user += {{
            location : u.location,
            followers : u.followers_count,
            description : u.description,
            following : u.friends_count,
            time_zone : u.time_zone,
            statuses_count : u.statuses_count,
            verified : u.verified
        }}
        MERGE (user)-[:POSTS]->(tweet)""".format(partition_key)
#     print 'user', userstr
    return userstr

def placeQuery(partition_key):
    
    placestr = """
        FOREACH (pid IN p.id |
            MERGE (place:Place_{0}:Place {{id:p.id}})
            ON CREATE SET place.url=p.url,
                place.id_str=p.id,
                place.place_type=p.place_type,
                place.country=p.country,
                place.name=p.name,
                place.full_name=p.full_name,
                place.country_code=p.country_code,
                place.country=p.country
            MERGE (tweet)-[:LOCATED_IN]->(place)
        )""".format(partition_key)
#     print 'place', placestr
    return placestr

def sourceQuery(partition_key):
    
    sourcestr = """
        MERGE (source:Source_{0}:Source {{source:t.source}})
        MERGE (tweet)-[:USING]->(source)""".format(partition_key)
#     print 'source', sourcestr
    return sourcestr

def entitiesQuery(partition_key):
    
    entitiesstr = """
        FOREACH (h IN e.hashtags |
            MERGE (tag:Hashtag_{0}:Hashtag {{name:LOWER(h.text)}})
            MERGE (tag)-[:TAGS{{indices:h.indices}}]->(tweet)
        )
        FOREACH (u IN e.urls |
            MERGE (url:Link_{0}:Link {{url:u.expanded_url}})
            MERGE (tweet)-[:CONTAINS{{indices:u.indices}}]->(url)
        )
        FOREACH (m IN e.user_mentions |
            MERGE (mentioned:User_{0}:User {{screen_name:m.screen_name}})
            ON CREATE SET mentioned.name = m.name
            MERGE (tweet)-[:MENTIONS{{indices:m.indices}}]->(mentioned)
        )""".format(partition_key)
#     print 'entitities', entitiesstr
    return entitiesstr

def replytoQuery(partition_key):
    
    replytostr = """
        FOREACH (r IN [r IN [t.in_reply_to_status_id_str] WHERE r IS NOT NULL] |
            MERGE (reply_tweet:Tweet_{0}:Tweet {{id_str:r}})
            MERGE (tweet)-[:REPLY_TO]->(reply_tweet)
        )""".format(partition_key)
#     print 'replyto', replytostr
    return replytostr

def retweetQuery(partition_key):
    
    retweetstr = """
    FOREACH (retweet_id IN [x IN [retweet.id_str] WHERE x IS NOT NULL] |
            MERGE (retweet_tweet:Tweet_{0}:Tweet {{id_str:retweet_id}})
            MERGE (tweet)-[:RETWEETS]->(retweet_tweet)
        )""".format(partition_key)
#     print 'retweet', retweetstr
    return retweetstr
        
def runQuery(graph,tweets, partition_key):
    
# Pass dict to Cypher and build query.
    query = """
        WITH {json} as data
        UNWIND data.tweets as t 
        WITH t
        ORDER BY t.id
        WITH t,
             t.entities AS e,
             t.user AS u,
             t.place AS p,
             t.retweeted_status AS retweet
    """\
    + tweetQuery(partition_key)\
    + userQuery(partition_key)\
    + placeQuery(partition_key)\
    + sourceQuery(partition_key)\
    + entitiesQuery(partition_key)\
    + replytoQuery(partition_key)\
    + retweetQuery(partition_key)
    
    #print query
    
    try:
        params = dict(json=tweets)
        graph.cypher.execute(query, params)
        
    except Exception as e:
        print(e)
        
def writebatch(graph, linescount, start, databatch,partition_key,partitionsize):
    try:

        if (partitionsize > 0):
            partition_key = partition_key + '_' + str(linescount/partitionsize)
        
        runQuery(graph,databatch,partition_key)
                            
        databatch['tweets'] = []
                            
        print "{0} lines processed after {1} seconds.".format(linescount,time.time()-start)
   
    except:
        print "error at record {0}".format(linescount)
    
def main(argv):
    
    fname, password, remoteserver, readsize, batchsize, partition_key, constraints, partitionsize, startval = readargs(argv)
    print partition_key

    graph = authenticate(password, remoteserver)
    
    start = time.time()

# Connect to graph and add constraints.

    if (constraints):
        #dropConstraints(graph)
        setConstraints(graph, partition_key)
        
    databatch = {'tweets':[]}

    with open(fname, 'rb') as f:
        i = 0;
        j = 0;
  
        for line in f:  
                
            if ((line is None) or (j >= readsize)): #test end of file, write remaining data
                if (i>0):
                    writebatch (graph, j, start, databatch,partition_key,partitionsize)
                break

            j=j+1
            
            if (j >= startval):
                
                i=i+1

                try:

                    data = json.loads(line, encoding='utf8')

                    if ('limit' not in data.keys()):
                        addtweet(data,databatch)

                    if ((i == batchsize) or (i==readsize)): 
                        writebatch (graph, j, start, databatch,partition_key,partitionsize)
                        i = 0    

                except Exception as e:
                    print 'final error encountered...', e, j, "lines processed"
    
        end = time.time()
        print end - start
        
        
if __name__ == "__main__":
    main(sys.argv[1:])
    