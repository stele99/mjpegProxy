#!/usr/bin/python

from PIL import Image
import threading
import StringIO
import time
import urllib2
import base64
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
# -------------- CONFIGURATION START -------------------------------------------
# Thumbnail Width
TMBWIDTH  = 300
# Frames to fetch per Second (1-5 should be ok)
FPS       = 3

#Root Directory of the Files
HTTROOT   =  '/home/epple/mjpegsrv/httroot'
PORT      = 8085
# CAMS JPG URLS
cams = {
        
        "cam7" : { "url"  : "http://64.118.25.194/jpg/image.jpg",
                   "hires": "",
                   "user" : "" ,
                   "pwd"  : "" },     
        "cam8" : { "url"  : "http://217.7.233.140/record/current.jpg",
                   "hires": "",
                   "user" : "" ,
                   "pwd"  : "" },                       
        "cam9" : { "url"  : "http://217.89.94.116/record/current.jpg",
                   "hires": "",
                   "user" : "" ,
                   "pwd"  : "" },                     
                                      
      }
      
# Define Users and Passwords      
users = { "guest" : "guest",
          "user"  : "userpassword"
        }      
#Realm for Authentication , put realm to empty to disable auth
realm = "Authenticated Site"
# -------------- CONFIGURATION END  -------------------------------------------
class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
      if realm and not self.check_basic_auth():
        return
      
      pathReq = self.path
      if pathReq == ('') or pathReq == '/':
        pathReq = '/index.html'
      
      if pathReq.find('?') > 0 :
         pathReq = pathReq[0:pathReq.find('?')]

      cam = pathReq[1:pathReq.find('.')]
      url = ''
      if cam in cams: 
        url = cams[cam]["url"]
      print "Processing Camera: " + cam + ". URL: " + url        

# --- SERVE: HTML ---------------------------------------------------------------      
      if pathReq.endswith('.html'):
        try:
          realpath = HTTROOT + pathReq
          print "Serve " + realpath
          with open(realpath, 'rb') as file: 
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            htmlcont = file.read()
            
            # include cams
            if pathReq.endswith('index.html'):
              htmlcam = ''
              for wc in sorted(cams):
                htmlcam = htmlcam + '<div class="cam"><img class="camimg" data-cam="' + wc + '" src="cache/' + wc + '.jpeg"/></div>'  
              htmlcont = htmlcont.replace('%CAMS%', htmlcam)
              
            self.wfile.write(htmlcont)        
        except:
          self.send_response(404)
        return

# --- SERVE STATIC FILES -------------------------------------------------------
      if pathReq.endswith('.jpeg') or pathReq.endswith('.gif') or pathReq.endswith('.js') or pathReq.endswith('.css') or pathReq.endswith('.ico') or pathReq.endswith('.png'):
        try:
          realpath = HTTROOT + pathReq
          print "Serve " + realpath
          with open(realpath, 'rb') as file: 
            self.send_response(200)
            if pathReq.endswith('.jpeg'):
              self.send_header('Content-type', 'image/jpeg')
            if pathReq.endswith('.gif'):
              self.send_header('Content-type', 'image/gif')
            if pathReq.endswith('.js'):
              self.send_header('Content-type', 'text/javascript')
            if pathReq.endswith('.css'):
              self.send_header('Content-type', 'text/css')
            if pathReq.endswith('.png'):
              self.send_header('Content-type', 'image/png')
            if pathReq.endswith('.css'):
              self.send_header('Content-type', 'image/x-icon')                                        
            self.end_headers()
            fcont = file.read()
            self.wfile.write(fcont)        
        except:
          self.send_response(404)
        return

      
# --- SERVE: JPG ---------------------------------------------------------------      
      if pathReq.endswith('.jpg'):
        self.send_response(200)
        self.send_header('Content-type','image/jpeg')
        try:
          req  = urllib2.Request(url)
          if cams[cam]["user"]:
             base64string = base64.encodestring('%s:%s' % (cams[cam]["user"], cams[cam]["pwd"])).replace('\n', '')
             req.add_header("Authorization", "Basic %s" % base64string)            
          res  = urllib2.urlopen(req)
          jpg  = res.read()
          img  = Image.open(StringIO.StringIO(jpg))
        except:
          print "Error reading Source JPG"
          img  = Image.open(HTTROOT+'/nocam.jpg')
        
        wpercent = (TMBWIDTH / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((TMBWIDTH, hsize), Image.ANTIALIAS)
        imgTmp = StringIO.StringIO()
        img.save(imgTmp,'JPEG')
        imgsize = imgTmp.len
        self.send_header('Content-length',imgsize)
        self.end_headers()
        img.save(self.wfile,'JPEG')
        img.save(HTTROOT + "/cache/" + cam + ".jpeg", 'JPEG')
        return

# --- SERVE: FULL  -------------------------------------------------------------
      if pathReq.endswith('.full'):
          self.send_response(200)
          self.send_header('Content-type','text/html')
          self.end_headers()
          self.wfile.write('<html><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"><head><script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.0/jquery.min.js"></script></head><body>')
          self.wfile.write('<img style="width:100%;height:auto;" class="imgfull" src="' + cam + '.mjpg">') 
          self.wfile.write('</body></html>')
          return;

# --- SERVE: MJPEG  -------------------------------------------------------------
      if pathReq.endswith('.mjpg') or pathReq.endswith('.hmjpg'):
        self.send_response(200)
        self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
        self.end_headers()
        
        print "Streaming Motion JPEG for Camera: " + cam + ". URL: " + url
        if  pathReq.endswith('.hmjpg'):
          if len(cams[cam]["hires"]) > 0:
            url = cams[cam]["hires"] 
          print 'URL:' + url
          
        #Maximum 5 Mins
        t_end = time.time() + 60 * 5
        while time.time() < t_end:
          try:
            self.wfile.write("--jpgboundary")
            req  = urllib2.Request(url)
            if cams[cam]["user"]:
               base64string = base64.encodestring('%s:%s' % (cams[cam]["user"], cams[cam]["pwd"])).replace('\n', '')
               req.add_header("Authorization", "Basic %s" % base64string)            
            res  = urllib2.urlopen(req)
            size = res.headers['content-length']
            jpg  = res.read()
          except:
            print "Error reading source for MJPG"
          
          try:
            self.send_header('Content-type','image/jpeg')
            self.send_header('Content-length',size)
            self.end_headers()
            self.wfile.write(jpg)
          except:
            print "exception openPipe"
            break
            return
          time.sleep(1 / FPS)  
        return
        
    def check_basic_auth(self):
      auth_hdr = self.headers.getheader('Authorization')
      if auth_hdr:
          method, auth = auth_hdr.split(" ", 1)
          if method.lower()=="basic":
            username, password = auth.decode("base64").split(":", 1)
            if username in users and users[username]==password:
              return True
      self.send_response(401)
      self.send_header('WWW-Authenticate', 'Basic realm=\"%s\"' % realm)
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      return False

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    server = ThreadedHTTPServer(('', PORT), Handler)
    print 'Starting server, use <Ctrl-C> to stop'
    try:
      server.serve_forever()
    except KeyboardInterrupt:
      pass

