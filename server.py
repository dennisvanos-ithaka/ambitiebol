"""Ambitiebol: dependency-light live workshop application."""
import io, csv, json, os, secrets, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import qrcode

ROOT=Path(__file__).parent
DATA=Path(os.environ.get('DATA_FILE', str(ROOT/'workshop-data.json')))
HOST_KEY=os.environ.get('HOST_KEY') or secrets.token_urlsafe(18)
PORT=int(os.environ.get('PORT','8080'))
LOCK=threading.RLock()
THEMES=[
 {'id':'autonomie','name':'Autonomie','short':'Autonomie','color':'#52BBA9','questions':[
  'We geven collega’s de komende acht weken meer ruimte om professionele keuzes te maken en die met elkaar te onderbouwen.',
  'We laten leerlingen vaker zelf keuzes maken over de aanpak van hun leerdoel, binnen duidelijke kaders.',
  'We kunnen leerlingen beter begeleiden om verantwoordelijkheid te nemen voor hun gedrag en de gevolgen ervan.',
  'We bespreken als team waar zelfstandigheid wenselijk is en waar een leerling juist structuur of begeleiding nodig heeft.',
  'We laten leerlingen vaker zelf terugkijken op hun vooruitgang en een haalbare volgende stap formuleren.']},
 {'id':'pedagogiek','name':'Pedagogisch handelen','short':'Pedagogiek','color':'#F09B76','questions':[
  'We bespreken vaker hoe we leerlingen begeleiden naar een zelfstandig en verantwoordelijk volwassen bestaan.',
  'We maken het pedagogisch klimaat van onze school vaker onderwerp van een open teamgesprek.',
  'We nemen de tijd om pedagogische casussen te bespreken zonder direct naar een oplossing te springen.',
  'We stemmen ons handelen bij grensoverschrijdend of lastig gedrag beter op elkaar af.',
  'We kijken bij pedagogische vraagstukken bewuster naar de relatie en de behoefte achter het gedrag van de leerling.']},
 {'id':'didactiek','name':'Didactiek','short':'Didactiek','color':'#E8B75C','questions':[
  'We besteden de komende acht weken meer aandacht aan wat een goede les voor onze leerlingen effectief maakt.',
  'We ontwikkelen en verbeteren lesmateriaal vaker samen, in plaats van ieder voor zich.',
  'We benutten leerdoelen en succescriteria duidelijker zodat leerlingen weten wat ze leren en wanneer het lukt.',
  'We onderzoeken vaker of onze instructie en werkvormen aansluiten bij de uiteenlopende taal- en onderwijsniveaus.',
  'We geven leerlingen gerichter feedback en controleren of die feedback hen daadwerkelijk verder helpt.']},
 {'id':'verbinding','name':'Verbinding','short':'Verbinding','color':'#86A8EB','questions':[
  'We maken de komende acht weken bewuster tijd voor echt contact tussen collega’s, ook buiten ons eigen kernteam.',
  'We investeren in kleine dagelijkse contactmomenten waardoor leerlingen zich gezien en welkom voelen.',
  'We creëren vaker momenten waarop leerlingen en medewerkers elkaar buiten de les op een andere manier leren kennen.',
  'We organiseren of stimuleren laagdrempelige teamactiviteiten die de onderlinge verbinding versterken.',
  'We spreken elkaar gemakkelijker aan en durven vragen te stellen vanuit vertrouwen en nieuwsgierigheid.']},
 {'id':'scholing','name':'Scholing','short':'Scholing','color':'#B18DE5','questions':[
  'We maken van lesbezoeken een laagdrempelige manier om van de praktijk te leren.',
  'We plannen vaker intervisie waarin we een eigen leervraag of dilemma kunnen onderzoeken.',
  'We geven zelfzorg, werkdruk en duurzame inzetbaarheid ook een plek in onze professionele ontwikkeling.',
  'We vertalen inzichten uit trainingen en studiedagen vaker naar concrete veranderingen in onze lessen.',
  'We nemen ieder bewuster eigenaarschap over één persoonlijk ontwikkelpunt en delen de voortgang.']},
 {'id':'expertise','name':'Expertise','short':'Expertise','color':'#D986AE','questions':[
  'We brengen beter in kaart welke kennis, vaardigheden en talenten in ons team aanwezig zijn.',
  'We vragen collega’s gerichter om mee te denken vanuit hun specifieke kwaliteiten.',
  'We gebruiken lesbezoeken om elkaars sterke kanten te herkennen en die vervolgens zelf uit te proberen.',
  'We spreken onderling hoge maar haalbare verwachtingen uit over ons professionele handelen.',
  'We delen vaker voorbeelden van wat goed werkt, inclusief waarom het volgens ons werkt.']},
 {'id':'organisatie','name':'Organisatie','short':'Organisatie','color':'#78B8B0','questions':[
  'We maken de jaarplanning overzichtelijker en vertalen die naar heldere prioriteiten per periode.',
  'We maken duidelijker wie waarvoor inzetbaar en verantwoordelijk is binnen het team.',
  'We stemmen werkzaamheden en beschikbare tijd beter op elkaar af om piekbelasting te beperken.',
  'We zorgen dat teamafspraken eenvoudig terug te vinden zijn en ook in de praktijk worden opgevolgd.',
  'We houden bij veranderingen in roosters, taken of leerlingaantallen beter zicht op de gevolgen voor onderwijskwaliteit.']}
]

def fresh():
 return {'code':secrets.token_hex(3).upper(),'phase':'reflectie','created':time.time(),'responses':{},'starts':{},'groups':[],'focus':[],'ambitions':{},'revision':0}

def load():
 try:
  d=json.loads(DATA.read_text(encoding='utf8'))
  if isinstance(d,dict) and 'code' in d:
   d.setdefault('starts',{})
   d.setdefault('focus',[])
   d.setdefault('ambitions',{})
   if d.get('phase')=='groepen':d['phase']='bespreken'
   return d
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
 return {'code':STATE['code'],'phase':STATE['phase'],'revision':STATE['revision'],'themes':THEMES,'summary':summary(),'participants':len(STATE['responses']),'completed':sum(all(f'{t["id"]}-{i}' in r.get('answers',{}) for t in THEMES for i in range(5)) for r in STATE['responses'].values()),'groups':STATE['groups'],'focus':STATE.get('focus',[]),'ambitions':STATE.get('ambitions',{})}

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
  if path in ('/api/export/raw.csv','/api/export/ambities.csv'):
   if not secrets.compare_digest(urllib.parse.parse_qs(url.query).get('key',[''])[0],HOST_KEY):self.reply({'error':'geen toegang'},403);return
   with LOCK:
    buf=io.StringIO();writer=csv.writer(buf,delimiter=';')
    if path.endswith('raw.csv'):
     writer.writerow(['deelnemer_anoniem','thema','stelling_nummer','stelling','antwoord_1_tot_4','bijgewerkt_unix'])
     for i,(uid,resp) in enumerate(STATE['responses'].items(),1):
      for theme in THEMES:
       for j,question in enumerate(theme['questions']):
        key=f"{theme['id']}-{j}"
        if key in resp.get('answers',{}):writer.writerow([f'Deelnemer {i}',theme['name'],j+1,question,resp['answers'][key],resp.get('updated','')])
    else:
     writer.writerow(['thema','ambitie_nummer','concrete_ambitie','periode','aandeel_aandacht_pct'])
     stats=summary();weights={t['id']:max(0,(t['mean'] or 1)-1) for t in stats};total=sum(weights.values())
     for theme_id in STATE.get('focus',[]):
      theme=next((t for t in THEMES if t['id']==theme_id),None)
      if theme:
       for j,note in enumerate(STATE.get('ambitions',{}).get(theme_id,[]),1):
        if note.strip():writer.writerow([theme['name'],j,note,'Komende 8 weken',round(100*weights[theme_id]/total,2) if total else 0])
    payload='\ufeff'+buf.getvalue()
    name='ambitiebol_ruwe_antwoorden.csv' if path.endswith('raw.csv') else 'ambitiebol_ambities.csv'
    data=payload.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/csv; charset=utf-8');self.send_header('Content-Disposition',f'attachment; filename="{name}"');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
   return
  if path=='/health':self.reply({'ok':True});return
  self.reply({'error':'not found'},404)
 def do_POST(self):
  path=urllib.parse.urlsplit(self.path).path;data=self.body()
  if path=='/api/start':
   uid=data.get('uid');code=data.get('code')
   if not isinstance(uid,str) or not 12<=len(uid)<=80:self.reply({'error':'ongeldige deelnemer'},400);return
   with LOCK:
    if code!=STATE['code']:self.reply({'error':'sessiecode onjuist'},403);return
    starts=STATE.setdefault('starts',{})
    if uid not in starts:
     starts[uid]=len(starts)%len(THEMES)
     update()
    self.reply({'start':starts[uid]});return
  if path=='/api/answer':
   uid=data.get('uid');code=data.get('code');answers=data.get('answers')
   if not isinstance(uid,str) or len(uid)>80 or len(uid)<12 or not isinstance(answers,dict):self.reply({'error':'ongeldige invoer'},400);return
   if len(answers)>sum(len(t['questions']) for t in THEMES) or any(k not in {f'{t["id"]}-{i}' for t in THEMES for i in range(5)} or type(v)!=int or v not in [1,2,3,4] for k,v in answers.items()):self.reply({'error':'ongeldige antwoorden'},400);return
   with LOCK:
    if code!=STATE['code']:self.reply({'error':'sessiecode onjuist'},403);return
    if STATE['phase']!='reflectie':self.reply({'error':'de reflectie is gesloten'},409);return
    STATE['responses'][uid]={'answers':answers,'updated':time.time()};update();self.reply({'ok':True,'count':len(answers)});return
  if path.startswith('/api/host/'):
   if not self.auth():self.reply({'error':'hostsleutel onjuist'},403);return
   with LOCK:
    if path=='/api/host/phase':
     if data.get('phase') not in ('reflectie','bespreken','afgerond'):self.reply({'error':'ongeldige fase'},400);return
     requested=data['phase']
     if requested in ('bespreken','afgerond') and not STATE.get('focus'):
      eligible=[t['id'] for t in summary() if t['mean'] is not None]
      STATE['focus']=eligible[:2]
      STATE['ambitions']={t:['','',''] for t in STATE['focus']}
     STATE['phase']=requested;update()
    elif path=='/api/host/ambitions':
     if STATE['phase']!='afgerond':self.reply({'error':'open eerst de afrondfase'},409);return
     theme=data.get('theme');items=data.get('items')
     if theme not in STATE.get('focus',[]) or not isinstance(items,list) or not 1<=len(items)<=30 or any(not isinstance(item,str) or len(item)>1500 for item in items):self.reply({'error':'ongeldige ambitie-invoer'},400);return
     STATE.setdefault('ambitions',{})[theme]=items;update()
    elif path=='/api/host/reset':
     STATE.clear();STATE.update(fresh());update()
    else:self.reply({'error':'onbekende actie'},404);return
    self.reply(public());return
  self.reply({'error':'not found'},404)

if __name__=='__main__':
 print(f'Open lokaal: http://localhost:{PORT}/host?key={HOST_KEY}',flush=True)
 print('Stel HOST_KEY in als omgevingsvariabele voor een vaste hostlink.',flush=True)
 ThreadingHTTPServer(('0.0.0.0',PORT),App).serve_forever()
