import time
import datetime
from datetime import datetime
import pytz

class tweetparser:
        
    def __init__(self):
        self.initNodelists()
        self.initRellists()
           
    def timestampUTC(self, datestring):
        
        dt = datetime.strptime(datestring,'%a %b %d %H:%M:%S +0000 %Y')
        epoch = datetime.utcfromtimestamp(0)
        return int( (dt - epoch).total_seconds() * 1000.0)
    
    def timekey(self, ts):
        UTC = pytz.timezone('GMT')
        dt = datetime.fromtimestamp(ts / 1000, UTC)
        tt = dt.timetuple()
        return str(tt[0])+'_'+str(tt[1])+'_'+str(tt[2])
     
    def getPartitionKey(self, tweet):
        ts = self.timestampUTC(tweet['created_at'])
        return self.timekey(ts)
        
    def initNodelists(self):
        self.nodelists = {}
        self.nodelists['Tweet']=[]
        self.nodelists['User']=[]
        self.nodelists['Source']=[]
        self.nodelists['Place']=[]
        self.nodelists['Hashtag']=[]
        self.nodelists['Link']=[]
        self.nodelists['UserMention']=[]
        
    def initRellists(self):
        self.rellists = {}
        self.rellists['POSTS']=[]
        self.rellists['USING']=[]
        self.rellists['LOCATED_IN']=[]
        self.rellists['TAGS']=[]
        self.rellists['CONTAINS']=[]
        self.rellists['MENTIONS']=[]
        self.rellists['RETWEETS']=[]
        self.rellists['REPLY_TO']=[]
        
    def clear(self):
        del self.nodelists['Tweet'][:]
        del self.nodelists['User'][:]
        del self.nodelists['Source'][:]
        del self.nodelists['Place'][:]
        del self.nodelists['Hashtag'][:]
        del self.nodelists['Link'][:]
        del self.nodelists['UserMention'][:]
        del self.rellists['POSTS'][:]
        del self.rellists['USING'][:]
        del self.rellists['LOCATED_IN'][:]
        del self.rellists['TAGS'][:]
        del self.rellists['CONTAINS'][:]
        del self.rellists['MENTIONS'][:]
        del self.rellists['RETWEETS'][:]
        del self.rellists['REPLY_TO'][:]
    
    def labelvalue(self, labelbase):
        
        return labelbase + "_" + str(self.partition_key)
    
    
    def idvalue(self, idbase, labelbase):
        
        return idbase + ":ID(" + self.labelvalue(labelbase) + ")"
    
    
    def relvalue(self, relbase, labelbase):
        
        return ":" + relbase + "(" + self.labelvalue(labelbase) + ")"
    
    
    def parseHashtag(self, parsedtweet, hashtag):
        
        labelvalue = self.labelvalue('Hashtag')
        startid = self.relvalue("START_ID","Hashtag")
        endid = self.relvalue("END_ID","Tweet")
        hashtagid = self.idvalue('name','Hashtag')
        tweetid = self.idvalue('id_str', 'Tweet')
        
        #print labelvalue,startid,endid,hashtagid,tweetid
        
        parsedtag= {\
                ":LABEL": labelvalue,\
                hashtagid: hashtag['text'].lower()
               }
        
#         print parsedtag

        self.rellists['TAGS'].append({startid:parsedtag[hashtagid], \
                                      endid:parsedtweet[tweetid], \
                                      ":TYPE":"TAGS"})
#         print parsedtag
        
        self.nodelists['Hashtag'].append(parsedtag)

        return parsedtag


    def parseLink(self, parsedtweet, link):
        
        labelvalue = self.labelvalue('Link')
        startid = self.relvalue("START_ID","Tweet")
        endid = self.relvalue("END_ID","Link")
        linkid = self.idvalue('url','Link')
        tweetid = self.idvalue('id_str', 'Tweet')
        
#         print labelvalue,startid,endid,linkid,tweetid

        parsedlink = {\
                ":LABEL": labelvalue,\
                linkid: link['expanded_url']
               }

        self.rellists['CONTAINS'].append({startid:parsedtweet[tweetid], \
                                          endid:parsedlink[linkid], \
                                          ":TYPE":"CONTAINS"})

        self.nodelists['Link'].append(parsedlink)

        return parsedlink


    def parseMention(self, parsedtweet, mention):

        labelvalue = self.labelvalue('UserMention')
        startid = self.relvalue("START_ID","Tweet")
        endid = self.relvalue("END_ID","User")
        mentionid = self.idvalue('screen_name','UserMention')
        tweetid = self.idvalue('id_str', 'Tweet')
        
#         print labelvalue,startid,endid,mentionid,tweetid
        mentionval=''
        if (mention['name']!= None):
            mentionval = '"""' + mention['name'] + '"""'
            
        parsedmention = {\
                ":LABEL": labelvalue,\
                mentionid: mention['screen_name'].lower(),\
                "name": mentionval
               }

        self.rellists['MENTIONS'].append({startid:parsedtweet[tweetid], \
                                          endid:parsedmention[mentionid], \
                                          ":TYPE":"MENTIONS"})

        self.nodelists['UserMention'].append(parsedmention)

        return parsedmention

                                          
    def parseSource(self, parsedtweet, source):
        
        sourceid = self.idvalue('source','Source')
        sourcelabel = self.labelvalue('Source')
        startid = self.relvalue('START_ID', 'Tweet')
        endid = self.relvalue('END_ID', 'Source')
        tweetid = self.idvalue('id_str','Tweet')
#         print sourceid, sourcelabel, startid, endid, tweetid
        
        parsedsource = {\
                ":LABEL": sourcelabel,\
                sourceid: source
               }
        
        self.rellists['USING'].append({startid:parsedtweet[tweetid], \
                                           endid:parsedsource[sourceid], \
                                           ":TYPE":"USING"})

        self.nodelists['Source'].append(parsedsource)

    def parsePlace(self, parsedtweet, place):
        
        placeid = self.idvalue('id','Place')
        placelabel = self.labelvalue('Place')
        startid = self.relvalue('START_ID', 'Tweet')
        endid = self.relvalue('END_ID', 'Place')
        tweetid = self.idvalue('id_str','Tweet')
#         print placeid, placelabel, startid, endid, tweetid
        
        parsedplace = {\
                ":LABEL": placelabel,\
                placeid: place["id"],\
                "place_type": place["place_type"],\
                "country": place["country"],\
                "name": place["name"],\
                "full_name": place["full_name"],\
                "country_code": place["country_code"]
               }

        self.rellists['LOCATED_IN'].append({startid:parsedtweet[tweetid], \
                                    endid:parsedplace[placeid], \
                                    ":TYPE":"LOCATED_IN"})

        self.nodelists['Place'].append(parsedplace)

        return parsedplace


    def parseEntities(self, parsedtweet, entities):

        if ('hashtags' in entities):
            for hashtag in entities['hashtags']:
                parsedtag=self.parseHashtag(parsedtweet, hashtag)

        if ('urls' in entities):
            for link in entities['urls']:
                parsedlink=self.parseLink(parsedtweet, link)

        if ('user_mentions' in entities):
            for mention in entities['user_mentions']:
                parsedmention=self.parseMention(parsedtweet, mention)

    def parseDescription(self, user):
        
        description_text = ''
                                          
        if (('description' in user) and (user["description"]!=None)):
                                          
                description=user["description"]
                                          
                if (len(description)>0):
                    description_text ='"' + description.replace('\\"', '""').rstrip('\\') + ' "'
                    description_text ='"' + description_text.replace('\n',' ')
                                          
        return description_text
    
    
    def parseLocation(self, user):
        
        location_text = ''
                                          
        if (('location' in user) and (user["location"]!=None)):
                                          
                location=user["location"]
                                          
                if (len(location)>0):
                    location_text ='"' + location.replace('\\"', '""').rstrip('\\') + ' "'
                                          
        return location_text
        
        
    def parseUser(self, parsedtweet, user):

        parseduser = {}
        
        userlabel = self.labelvalue('User')
        userid = self.idvalue('screen_name', 'User')
        startid = self.relvalue("START_ID","User")
        endid = self.relvalue("END_ID","Tweet")
        tweetid = self.idvalue('id_str', 'Tweet')
#         print userlabel, userid, startid, endid, tweetid
        
        #must have unique id defined
        if (('screen_name' in user) and (user['screen_name'] != None) and (len(user['screen_name'])>0)):
            
            parseduser = {\
                    ":LABEL": userlabel,\
                     userid: user["screen_name"].lower(),\
                    "location": self.parseLocation(user),\
                    "followers": int(user["followers_count"]),\
                    "following": int(user["friends_count"]),\
                    "time_zone": user["time_zone"],\
                    "statuses_count": int(user["statuses_count"]),\
                    "verified": user["verified"],\
                    "description": self.parseDescription(user)\
                   }

            self.rellists['POSTS'].append({startid:parseduser[userid], \
                                           endid:parsedtweet[tweetid], \
                                           ":TYPE":"POSTS"})

            self.nodelists['User'].append(parseduser)

        return parseduser

                                          
    def parseText(self, tweet):
        
        tweettext = ''
                                          
        if (tweet["text"]!=None):
                              
            if (len(tweet["text"])>0):
                text = tweet["text"]
                tweettext = text.replace('\\"', '""').rstrip('\\')
                tweettext = tweettext.replace('\n', ' ')
                                          
        return '"' + tweettext + ' "'
           

    def parseTweetTime(self, tweet):
                                          
        ts = 0
                                          
        if 'timestamp_ms' in tweet:
            ts = long(tweet['timestamp_ms'])
                                          
        elif 'created_at' in tweet:
            ts = self.timestampUTC(tweet['created_at'])

        return ts
                 
                                          
    def parseRetweet(self, tweet):

        startid = self.relvalue('START_ID', 'Tweet')
        endid = self.relvalue('END_ID', 'Tweet')
        
        retweet_id = 0
                                          
        if ('retweeted_status' in tweet):

            status = tweet['retweeted_status']

            if ('id_str' in status):

                retweet_id = int(status['id_str'])

                self.rellists['RETWEETS'].append({startid:tweet['id_str'], \
                                              endid:retweet_id, \
                                              ":TYPE":"RETWEETS"})
        
        return retweet_id
                                          

    def parseReplyTo(self, tweet):

        startid = self.relvalue('START_ID', 'Tweet')
        endid = self.relvalue('END_ID', 'Tweet')
        
        reply_to_str = ''
                                          
        if ('in_reply_to_status_id_str' in tweet):

            reply_to = tweet['in_reply_to_status_id_str']

            if ((reply_to != None) and (reply_to != '') and (len(reply_to) > 0)):
                
                reply_to_str = str(reply_to)
                
                self.rellists['REPLY_TO'].append({startid:tweet['id_str'], \
                                        endid:reply_to_str, \
                                        ":TYPE":"REPLY_TO"})
        return reply_to_str
                                          
                                          
    def parseTweet(self, tweet):

        tweetlabel = self.labelvalue('Tweet')
        tweetid = self.idvalue('id_str', 'Tweet')
#         print tweetlabel, tweetid
        
        parsedtweet={\
                ":LABEL": tweetlabel,\
                tweetid: tweet['id_str'],\
                "created_at": tweet['created_at'], \
                "favorite_count": tweet['favorite_count'],\
                "text" : self.parseText(tweet),\
                "in_reply_to_status_id_str" : self.parseReplyTo(tweet)
               }

        #Timestamp
        ts = self.parseTweetTime(tweet)
        if (ts > 0):
            parsedtweet['timestamp_int'] = ts
        else:
            parsedtweet['timestamp_int'] = ''
        
        #Retweet
        rt = self.parseRetweet(tweet)
        if (rt > 0):
            parsedtweet['retweet_id'] = rt
        else:
            parsedtweet['retweet_id'] = ''
        
        self.nodelists['Tweet'].append(parsedtweet)

        return parsedtweet


    def parseData(self, tweets, partition_key):

        for tweet in tweets: 
            try:
                self.partition_key = partition_key

                #print 'parsing tweet'
                parsedtweet=self.parseTweet(tweet)

                #print 'parsing user'
                parseduser=self.parseUser(parsedtweet, tweet['user'])

                if (('source' in tweet) and (tweet['source'] != None) and (len(tweet['source'])>0)):
                    parsedsource=self.parseSource(parsedtweet, tweet['source'])

                if (('place' in tweet) and (tweet['place'] != None)):
                    parsedplace=self.parsePlace(parsedtweet, tweet['place'])

                self.parseEntities(parsedtweet, tweet['entities'])

            except Exception as e:
                print e, tweet
            