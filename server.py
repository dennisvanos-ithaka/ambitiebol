"""Ambitiebol: dependency-light live workshop application."""
import io, json, os, secrets, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import qrcode

ROOT=Path(__file__).parent
DATA=Path(os.environ.get('DATA_FILE', str(ROOT/'workshop-data.json')))
HOST_KEY=os.environ.get('HOST_KEY') or secrets.token_urlsafe(18)
PORT=int(os.environ.get('PORT','8080'))
LOCK=threading.RLock()
THEMES=[
 {'id':'team','name':'Teamontwikkeling','short':'Samen leren','color':'#59b7bd','questions':[
  'De komende acht weken wil ik meer gebruikmaken van de kwaliteiten en expertise van collega’s.',
  'Het delen van succesvolle lesideeën verdient de komende acht weken extra aandacht.',
  'Lesbezoeken bij collega’s kunnen mijn handelen de komende acht weken versterken.',
  'Ik wil vaker praktijkcasussen met collega’s bespreken om samen te leren.',
  'We mogen de komende acht weken bewuster werken aan verbinding en onderling vertrouwen in het team.']},
 {'id':'pedagogiek','name':'Pedagogisch handelen','short':'Leerling centraal','color':'#efb668','questions':[
  'De sociaal-emotionele ontwikkeling van leerlingen verdient de komende acht weken extra gezamenlijke aandacht.',
  'We kunnen bewuster investeren in de relatie tussen docent en leerling en in een veilig leerklimaat.',
  'Ik wil leerlingen de komende acht weken meer verantwoordelijkheid laten nemen voor hun leerproces.',
  'We kunnen gezamenlijk sterker worden in hoge verwachtingen en leerbevorderende feedback.',
  'We kunnen leerlingen vaker uitdagen tot zelfstandig en verdiepend denken.']},
 {'id':'processen','name':'Professionele ontwikkeling en processen','short':'Slim samenwerken','color':'#ad91de','questions':[
  'De communicatie over de vorderingen van leerlingen verdient de komende acht weken extra aandacht.',
  'We kunnen leerlinginformatie in de OMU consistenter en bruikbaarder vastleggen.',
  'Ik wil de komende acht weken bijdragen aan het verbeteren van rapporten en portfolio’s.',
  'We kunnen duidelijker afspreken hoe we flexibel omgaan met de groei en veranderingen in onze school.',
  'Het bewuster inzetten van elkaars expertise kan ons werk doelgerichter maken.']}
]

def fresh():
 return {'code':secrets.token_hex(3).upper(),'phase':'reflectie','created':time.time(),'responses':{},'groups':[],'revision':0}

def load():
 try:
  d=json.loads(DATA.read_text(encoding='utf8'))
  if isinstance(d,dict) and 'code' in d: return d
 except (OSError,ValueError): pass
 return fresh()
STATE=load()
def save():
 tmp=DATA.with_suffix('.tmp');tmp.write_text(json.dumps(STATE,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,DATA)
def update():
 STATE['revision']+=1;save()
def summary():
 result=[]
 for t in THEMES:
  questions=[]; vals=[]; participation=set()
  for ix,q in enumerate(t['questions']):
   ratings=[r['answers'][f"{t['id']}-{ix}"] for uid,r in STATE['responses'].items() if isinstance(r.get('answers',{}).get(f"{t['id']}-{ix}"),int)]
   for uid,r in STATE['responses'].items():
    if f"{t['id']}-{ix}" in r.get('answers',{}):participation.add(uid)
   questions.append({'text':q,'mean':round(sum(ratings)/len(ratings),2) if ratings else None,'count':len(ratings),'distribution':[ratings.count(n) for n in range(1,5)]})
   vals.extend(ratings)
  result.append({'id':t['id'],'name':t['name'],'short':t['short'],'color':t['color'],'mean':round(sum(vals)/len(vals),2) if vals else None,'count':len(participation),'questions':questions})
 return sorted(result,key=lambda t:(t['mean'] is not None,t['mean'] or 0),reverse=True)

def public():
 return {'code':STATE['code'],'phase':STATE['phase'],'revision':STATE['revision'],'themes':THEMES,'summary':summary(),'participants':len(STATE['responses']),'completed':sum(len(r.get('answers',{}))==15 for r in STATE['responses'].values()),'groups':STATE['groups']}

class App(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args):pass
 def reply(self,data,status=200,ctype='application/json; charset=utf-8'):
  if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode()
  elif isinstance(data,str):data=data.encode()
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def body(self):
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>50000:return {}
   return json.loads(self.rfile.read(n))
  except (ValueError,TypeError):return {}
 def auth(self):
  return secrets.compare_digest(self.headers.get('X-Host-Key',''),HOST_KEY)
 def do_GET(self):
  url=urllib.parse.urlsplit(self.path);path=url.path
  if path in ('/','/host','/join'):
   self.reply((ROOT/'static'/'index.html').read_bytes(),ctype='text/html; charset=utf-8');return
  if path=='/api/state':
   with LOCK:self.reply(public());return
  if path=='/api/qr':
   query=urllib.parse.parse_qs(url.query);target=query.get('url',[''])[0]
   # Only encode app's own join path and compatible http(s) URL
   if not target.startswith(('http://','https://')):self.reply({'error':'invalid url'},400);return
   image=qrcode.make(target,box_size=7,border=2);out=io.BytesIO();image.save(out,format='PNG');self.reply(out.getvalue(),ctype='image/png');return
  if path=='/api/export':
   if not secrets.compare_digest(urllib.parse.parse_qs(url.query).get('key',[''])[0],HOST_KEY):self.reply({'error':'geen toegang'},403);return
   with LOCK:self.reply({'state':public(),'raw':STATE});return
  if path=='/health':self.reply({'ok':True});return
  self.reply({'error':'not found'},404)
 def do_POST(self):
  path=urllib.parse.urlsplit(self.path).path;data=self.body()
  if path=='/api/answer':
   uid=data.get('uid');code=data.get('code');answers=data.get('answers')
   if not isinstance(uid,str) or len(uid)>80 or len(uid)<12 or not isinstance(answers,dict):self.reply({'error':'ongeldige invoer'},400);return
   if len(answers)>15 or any(k not in {f'{t["id"]}-{i}' for t in THEMES for i in range(5)} or type(v)!=int or v not in [1,2,3,4] for k,v in answers.items()):self.reply({'error':'ongeldige antwoorden'},400);return
   with LOCK:
    if code!=STATE['code']:self.reply({'error':'sessiecode onjuist'},403);return
    if STATE['phase']!='reflectie':self.reply({'error':'de reflectie is gesloten'},409);return
    STATE['responses'][uid]={'answers':answers,'updated':time.time()};update();self.reply({'ok':True,'count':len(answers)});return
  if path=='/api/group':
   with LOCK:
    if data.get('code')!=STATE['code']:self.reply({'error':'sessiecode onjuist'},403);return
    if STATE['phase']!='groepen':self.reply({'error':'groepsfase is gesloten'},409);return
    record={k:str(data.get(k,'')).strip()[:1200] for k in ['group','theme','tomorrow','eightweeks','signal']}
    if record['theme'] not in [t['id'] for t in summary()[:2]] or not record['tomorrow'] or not record['eightweeks']:self.reply({'error':'vul de actie en achtwekenafspraak in'},400);return
    record['id']=secrets.token_hex(6);STATE['groups'].append(record);update();self.reply({'ok':True});return
  if path.startswith('/api/host/'):
   if not self.auth():self.reply({'error':'hostsleutel onjuist'},403);return
   with LOCK:
    if path=='/api/host/phase':
     if data.get('phase') not in ('reflectie','bespreken','groepen','afgerond'):self.reply({'error':'ongeldige fase'},400);return
     STATE['phase']=data['phase'];update()
    elif path=='/api/host/reset':
     STATE.clear();STATE.update(fresh());update()
    else:self.reply({'error':'onbekende actie'},404);return
    self.reply(public());return
  self.reply({'error':'not found'},404)

if __name__=='__main__':
 print(f'Open lokaal: http://localhost:{PORT}/host?key={HOST_KEY}',flush=True)
 print('Stel HOST_KEY in als omgevingsvariabele voor een vaste hostlink.',flush=True)
 ThreadingHTTPServer(('0.0.0.0',PORT),App).serve_forever()
