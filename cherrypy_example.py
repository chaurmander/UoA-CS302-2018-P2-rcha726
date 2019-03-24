#!/usr/bin/python
""" cherrypy_example.py

    COMPSYS302 - Software Design
    Author: Andrew Chen (andrew.chen@auckland.ac.nz)
    Last Edited: 19/02/2018

    This program uses the CherryPy web server (from www.cherrypy.org).
"""
# Requires:  CherryPy 3.2.2  (www.cherrypy.org)
#            Python  (We use 2.7)

# The address we listen for connections on
listen_ip = "0.0.0.0"
listen_port = 10010

import cherrypy
import hashlib
import urllib2
import socket
import requests
import sqlite3
import json
import datetime
import time
import jinja2
import base64
import mimetypes
from jinja2 import Environment, FileSystemLoader
import thread
class MainApp(object):

    #CherryPy Configuration
    _cp_config = {'tools.encode.on': True, 
                  'tools.encode.encoding': 'utf-8',
                  'tools.sessions.on' : 'True',
                 }                 

    # If they try somewhere we don't know, catch it here and send them to the right place.
    @cherrypy.expose
    def default(self, *args, **kwargs):
        """The default page, given when we don't recognise where the request is for."""
        Page = "I don't know where you're trying to go, so have a 404 Error."
        cherrypy.response.status = 404
        return Page

    # PAGES (which return HTML that can be viewed in browser)
    @cherrypy.expose
    def index(self):
        from jinja2 import Environment, FileSystemLoader
        file_loader = FileSystemLoader('Html')
        env = Environment(loader=file_loader)
        template = env.get_template('mainpage.html')
        try:
            self.displayUsers()
            Page = template.render(username=cherrypy.session['username'])

        except KeyError: #There is no username
            
            Page = "Click here to <a href='login'>login</a>."
        return Page
        
    @cherrypy.expose
    def login(self):
        Page = open('Html/loginHTML.html')
        return Page
    
    @cherrypy.expose    
    def sum(self, a=0, b=0): #All inputs are strings by default
        output = int(a)+int(b)
        return str(output)
        
    # LOGGING IN AND OUT
    @cherrypy.expose
    def signin(self, username=None, password=None, location=None):
        """Check their name and password and send them either to the main page, or back to the main login screen."""
        error = self.authoriseUserLogin(username, password, location)
        if error == 0:

            raise cherrypy.HTTPRedirect('/')
        else:
            raise cherrypy.HTTPRedirect('/login')

    @cherrypy.expose
    def displayUsers(self):
        file_loader = FileSystemLoader('Html')
        env = Environment(loader=file_loader)
        template = env.get_template('mainpage.html')
        username = cherrypy.session['username']
        hashed = cherrypy.session['password']
        conn = sqlite3.connect('userOnline.db')  # pass in a file when done, memory is current only for testing
        c = conn.cursor()
        c.execute("DROP TABLE usersOnline")
        c.execute("""CREATE TABLE usersOnline (
                     user text,
                     location text,
                     ip text,
                     port text,
                     lastLogin text
                     )""")

        seeUser = requests.get('http://cs302.pythonanywhere.com/getList?username='+username+'&password='+hashed+'&json=1')
        data=json.loads(seeUser.text)
        usernameList = []
        locationList = []
        ipList = []
        portList = []
        lastLoginList = []

        for i in range(0, len(data)):
            c.execute("INSERT INTO usersOnline VALUES (?,?,?,?,?)", (data[str(i)]['username'], data[str(i)]['location'], data[str(i)]['ip'], data[str(i)]['port'], data[str(i)]['lastLogin']))
            conn.commit()
            usernameList.append( data[str(i)]['username'])
            locationList.append(data[str(i)]['location'])
            ipList.append(data[str(i)]['ip'])
            portList.append(data[str(i)]['port'])
            value = datetime.datetime.fromtimestamp(int(data[str(i)]['lastLogin']))
            lastLoginList.append(value.strftime('%Y-%m-%d %H:%M:%S'))

        Page = template.render(usernameList=usernameList, locationList=locationList,ipList=ipList, portList=portList,lastLoginList=lastLoginList)
        return Page

    @cherrypy.expose
    def signout(self):
        """Logs the current user out, expires their session"""
        error = requests.get('http://cs302.pythonanywhere.com/logoff?username='+cherrypy.session['username']+'&password='+cherrypy.session['password'])
        if error.text == '0, Logged off successfully':

            cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect('/')
        
    def authoriseUserLogin(self, username, password, location):
        hashed = hashlib.sha256(password+username)
        cherrypy.session['username'] = username
        cherrypy.session['password'] = hashed.hexdigest()
        cherrypy.session['location'] = location
        if location == '0':
            ip = socket.gethostbyname(socket.gethostname())
        elif location == '1':
            ip = socket.gethostbyname(socket.gethostname())
            print (ip)
            print ('ip above')
        elif location == '2':
            ip = requests.get('http://ip.42.pl/raw').text


        loc = location
        port = '10010'
        cherrypy.session['port'] = port
        enc = '0'
        loginAuth = requests.get('http://cs302.pythonanywhere.com/report?username='+cherrypy.session['username']+'&password='+cherrypy.session['password']+'&ip='+ip+'&port='+port+'&location='+loc+'&enc='+enc)
        print(loginAuth.text)
        if loginAuth.text=='0, User and IP logged':
            print ('user logging in')
            return 0
        else:
            print ("unsuccessful login")
            return 1

    @cherrypy.tools.json_in()
    @cherrypy.expose
    def receiveMessage(self):
        input_data = cherrypy.request.json

        conn = sqlite3.connect('userOnline.db')  # pass in a file when done, memory is current only for testing
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS record (
                                     sender text,
                                     destination float,
                                     message text,
                                     stamp text
                                     )""")

        c.execute("INSERT INTO record VALUES (?,?,?,?)", (input_data['sender'], input_data['destination'], input_data['message'], input_data['stamp'],))
        conn.commit()



        print('Incoming Message')
        print(input_data['message'])
        print('Message End')
        return '0'

    @cherrypy.expose
    def sendMessage(self, userToSendTo=None, messageToSend=None):
 
        output_dict= {"sender": cherrypy.session['username'],"message": messageToSend,"recipient": userToSendTo, "destination": userToSendTo, "stamp": float(time.time())}
        data = json.dumps(output_dict) #data is a JSON object
        conn = sqlite3.connect('userOnline.db')
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS record (
                                     sender text,
                                     destination float,
                                     message text,
                                     stamp text
                                     )""")
        c.execute("INSERT INTO record VALUES (?,?,?,?)", (cherrypy.session['username'], userToSendTo, messageToSend, float(time.time()),))
        conn.commit()

        c.execute('SELECT * FROM usersOnline WHERE user=?', (userToSendTo,))
        k = c.fetchone()
        if (cherrypy.session['location']==k[1]):
            req = urllib2.Request('http://'+k[2]+':'+k[3]+'/receiveMessage', data, {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
            print('Message Sending')
            print('Recieved Message Value: '+response.read())
        else:
            print('Message unable to be sent location are not the same!')
	
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def ping(self, sender):
        print ('Someone has pinged me')
        print sender
        print ('Pinged has ended')
        return '0'

    @cherrypy.expose
    def sendPing(self):
        r = requests.get('http://10.103.137.36:10010/ping?sender=rcha726')
        print ('I am pinging someone')
        print ('Ping error value: '+r.text)

    @cherrypy.tools.json_in()
    @cherrypy.expose
    def getProfile(self, profile_username=None, sender=None):
        input_data = cherrypy.request.json
        print (input_data)
        
        
        conn = sqlite3.connect('userOnline.db')  # pass in a file when done, memory is current only for testing
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS userProfiles (
                             upi text,
                             lastUpdated float,
                             fullname text,
                             position text,
                             description text,
                             location text,
                             picture text
                             )""")
  
        c.execute("SELECT * FROM userProfiles WHERE upi=?", (input_data['profile_username'],))
        print('111111111111111')
        entry = c.fetchone()
        print(entry)

        if entry is None:
            c.execute("INSERT INTO userProfiles VALUES (?,?,?,?,?,?,?)",
                      (input_data['profile_username'], float(time.time()), 'No Name', 'No Position', 'No Description', 'No location', 'https://imgur.com/gallery/Ub7qC', ))
            conn.commit()
            c.execute("SELECT * FROM userProfiles WHERE upi=?", (input_data['profile_username'],))
            profilefromdb = c.fetchone()
            json_profile = {"lastUpdated": profilefromdb[1], "fullname": profilefromdb[2], "position": profilefromdb[3],
                            "description": profilefromdb[4], "location": profilefromdb[5], "picture": profilefromdb[6]}
            data = json.dumps(json_profile)
            print("creating new record")
            return data
        else:
            c.execute("SELECT * FROM userProfiles WHERE upi=?", (input_data['profile_username'],))
            profilefromdb = c.fetchone()
            print(profilefromdb)
            json_profile = {"lastUpdated": profilefromdb[1], "fullname" : profilefromdb[2], "position": profilefromdb[3], "description": profilefromdb[4], "location": profilefromdb[5], "picture": profilefromdb[6]}
            data = json.dumps(json_profile)
            print("returning existing record")
            return data

    @cherrypy.expose
    def getUserProfile(self, profile_username=None, sender=None):
        conn = sqlite3.connect('userOnline.db')
        c = conn.cursor()
        c.execute('SELECT * FROM usersOnline WHERE user=?', (profile_username,))
        k = c.fetchone()
        output_dict= {"profile_username": profile_username, "sender": cherrypy.session['username']}
        data = json.dumps(output_dict) #data is a JSON object
        req = urllib2.Request('http://'+k[2]+':'+k[3]+'/getProfile', data, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)

        file_loader = FileSystemLoader('Html')
        env = Environment(loader=file_loader)
        template = env.get_template('userSelfProfile.html')
        data = json.loads(response.read())
        
        Page = template.render(fullname=data['fullname'], position=data['position'],description=data['description'], location=data['location'],lastUpdated=data['lastUpdated'])
        return Page
            

    @cherrypy.tools.json_in()
    @cherrypy.expose
    def receiveFile(self):
        print("check 1")
        input_data = cherrypy.request.json

        fh = open("recievingFiles/"+input_data['filename'], "wb")
        fh.write(base64.decodestring(input_data['file']))
        fh.close()

        print('Incoming File')
        print(input_data['sender'])
        print(input_data['destination'])
        print(input_data['file'])
        print(input_data['filename'])
        print(input_data['content_type'])
        print(input_data['stamp'])  
        print('File End')
        return '0'
    
    @cherrypy.expose
    def sendFile(self, userToSendFile=None, filetouser=None):
        file_1 = filetouser
        print(file_1.content_type)
        filestring = base64.encodestring(file_1.file.read())

        content_type = str(mimetypes.guess_type(file_1.filename)[0])

        print (content_type)
        output_dict= {"sender": cherrypy.session['username'], "destination": userToSendFile, "file": filestring, "filename": file_1.filename, "content_type": content_type, "stamp": int(time.time())}
        data = json.dumps(output_dict) #data is a JSON object
        
        conn = sqlite3.connect('userOnline.db')
        c = conn.cursor()
        c.execute('SELECT * FROM usersOnline WHERE user=?', (userToSendFile,))
        k = c.fetchone()
        if (int(cherrypy.session['location'])==int(k[1])):
         
            req = urllib2.Request('http://'+k[2]+':'+k[3]+'/receiveFile', data, {'Content-Type': 'application/json'})

            
            response = urllib2.urlopen(req)
     
            print('Message Sending')
            print('Recieved Message Value: '+response.read())
        else:
            print('Message unable to be sent location are not the same!')
	
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def showSelfProfile(self):
        file_loader = FileSystemLoader('Html')
        env = Environment(loader=file_loader)
        template = env.get_template('userSelfProfile.html')
        selfProfile = self.getProfile(cherrypy.session['username'], cherrypy.session['username'])
        data = json.loads(selfProfile)
        value = datetime.datetime.fromtimestamp(data['lastUpdated'])
        Page = template.render(fullname=data['fullname'], position=data['position'], description=data['description'], picture=data['picture'], location=data['location'], lastUpdated=value)
        return Page

    @cherrypy.expose
    def showEditProfile(self):
        Page = open('Html/editProfile.html')
        return Page

    @cherrypy.expose
    def history(self, message_username=None):
        conn = sqlite3.connect('userOnline.db')
        c = conn.cursor()
        c.execute('SELECT * FROM record WHERE sender=? AND destination=?' , (cherrypy.session['username'],message_username,))
        selftouser=c.fetchall()
        c.execute('SELECT * FROM record WHERE sender=? AND destination=?' , (message_username,cherrypy.session['username'],))
        usertoself=c.fetchall()
        
        senderList = []
        messageList = []
      
        messages =  selftouser+usertoself
        k=sorted(messages, key=lambda message: messages[3])
        for n in range(0, len(messages)):
            senderList.append(messages[n][0])
            messageList.append(messages[n][2])
        

        file_loader = FileSystemLoader('Html')
        env = Environment(loader=file_loader)
        template = env.get_template('chat.html')

        Page = template.render(senderList=senderList, messageList=messageList)
        #return str(messages)
        return Page
            

    @cherrypy.expose
    def editProfile(self, nameedit=None, positionedit=None, descriptionedit=None, locationedit=None, pictureedit=None):
        conn = sqlite3.connect('userOnline.db')
        c = conn.cursor()
        print(positionedit)
        if nameedit :
            c.execute("""UPDATE userProfiles SET fullname=? WHERE upi=?""", (nameedit, cherrypy.session['username']))
            conn.commit()
        if positionedit:
            print("THis is executing")
            c.execute("""UPDATE userProfiles SET position=? WHERE upi=?""", (positionedit, cherrypy.session['username']))
            conn.commit()
        if descriptionedit:
            c.execute("""UPDATE userProfiles SET description=? WHERE upi=?""", (descriptionedit, cherrypy.session['username']))
            conn.commit()
        if locationedit:
            c.execute("""UPDATE userProfiles SET location=? WHERE upi=?""", (locationedit, cherrypy.session['username']))
            conn.commit()
        if pictureedit:
            c.execute("""UPDATE userProfiles SET picture=? WHERE upi=?""", (pictureedit, cherrypy.session['username']))
            conn.commit()
        c.execute("""UPDATE userProfiles SET lastUpdated=? WHERE upi=?""", (float(time.time()), cherrypy.session['username']))
        conn.commit()
        raise cherrypy.HTTPRedirect('/showSelfProfile')


def runMainApp():
    # Create an instance of MainApp and tell Cherrypy to send all requests under / to it. (ie all of them)
    cherrypy.tree.mount(MainApp(), "/")

    # Tell Cherrypy to listen for connections on the configured address and port.
    cherrypy.config.update({'server.socket_host': listen_ip,
                            'server.socket_port': listen_port,
                            'engine.autoreload.on': True,
                           })
    print "========================="
    print "University of Auckland"
    print "COMPSYS302 - Software Design Application"
    print "========================================"                       
    
    # Start the web server
    cherrypy.engine.start()

    # And stop doing anything else. Let the web server take over.
    cherrypy.engine.block()


#Run the function to start everything
runMainApp()
# why are we using login server vs others, How good or bad our demo, Hypothecially how to deal with login server outage
# what vulnerability is in your system
# strength and weakness to the language 
# how is data stored in your system
# how to scale your application


