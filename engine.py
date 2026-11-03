import os,re,sqlite3,requests,datetime as dt,statistics
from urllib.parse import urlparse
DB = "/tmp/smartwait.db"
API='https://api.mercadolibre.com'

def connect():
 os.makedirs(os.path.dirname(os.path.abspath(DB)),exist_ok=True)
 c=sqlite3.connect(DB,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA busy_timeout=10000');return c

def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,title TEXT NOT NULL,url TEXT, currency TEXT NOT NULL, last_price REAL,last_seen TEXT,source TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id TEXT NOT NULL,price REAL NOT NULL,currency TEXT NOT NULL,observed_at TEXT NOT NULL,source TEXT NOT NULL,FOREIGN KEY(product_id) REFERENCES products(id));
  CREATE INDEX IF NOT EXISTS idx_obs ON observations(product_id,observed_at);
  CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id TEXT NOT NULL,target REAL NOT NULL,created_at TEXT NOT NULL,triggered_at TEXT,active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,alert_id INTEGER NOT NULL,product_id TEXT NOT NULL,price REAL NOT NULL,created_at TEXT NOT NULL);''')

def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def ml_id(value):
 m=re.search(r'(?i)\b(MLA)[-_]?(\d{8,14})\b',value or '')
 if m:return (m.group(1)+m.group(2)).upper()
 return None

def fetch_ml(item_id,token):
 if not token:raise ValueError('Para consultar Mercado Libre necesitás configurar un access token autorizado. No se obtuvo un precio real.')
 if not re.fullmatch(r'MLA\d{8,14}',item_id):raise ValueError('Ingresá una publicación válida de Mercado Libre Argentina (MLA...).')
 headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'SmartWait-educational/3.0'}
 try:
  r=requests.get(f'{API}/items/{item_id}',headers=headers,timeout=12)
  if r.status_code==401:raise ValueError('La API de publicaciones (/items) devolvió HTTP 401: credencial no autorizada para este recurso.')
  if r.status_code==403:raise ValueError('La API de publicaciones (/items) devolvió HTTP 403: acceso denegado para esta publicación o aplicación.')
  if r.status_code==404:raise ValueError('No encontré esa publicación en Mercado Libre.')
  r.raise_for_status(); item=r.json()
  r=requests.get(f'{API}/items/{item_id}/sale_price',headers=headers,params={'context':'channel_marketplace'},timeout=12)
  if r.status_code==401:raise ValueError('La API de precios (/sale_price) devolvió HTTP 401: autorización insuficiente o inválida para este recurso.')
  if r.status_code==403:raise ValueError('La API de precios (/sale_price) devolvió HTTP 403: esta aplicación no tiene acceso a ese precio.')
  if r.status_code==404:raise ValueError('Mercado Libre no devolvió el precio de venta de esa publicación.')
  r.raise_for_status();price=r.json()
 except requests.RequestException as exc:raise ValueError(f'No pude verificar el precio con Mercado Libre ({type(exc).__name__}). No se guardaron datos.') from exc
 amount=price.get('amount');currency=price.get('currency_id')
 if not isinstance(amount,(int,float)) or amount<=0 or not currency:raise ValueError('La respuesta de Mercado Libre no contiene un precio verificable.')
 return {'id':item_id,'title':item.get('title') or item_id,'url':item.get('permalink') or f'https://www.mercadolibre.com.ar/','price':float(amount),'currency':currency,'source':'Mercado Libre API'}

def save(p):
 stamp=now()
 with connect() as c:
  old=c.execute('SELECT currency FROM products WHERE id=?',(p['id'],)).fetchone()
  if old and old['currency']!=p['currency']:raise ValueError('Cambió la moneda del producto; no se mezclaron precios incompatibles.')
  c.execute('''INSERT INTO products(id,title,url,currency,last_price,last_seen,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,url=excluded.url,last_price=excluded.last_price,last_seen=excluded.last_seen,source=excluded.source''',(p['id'],p['title'],p['url'],p['currency'],p['price'],stamp,p['source']))
  c.execute('INSERT INTO observations(product_id,price,currency,observed_at,source) VALUES(?,?,?,?,?)',(p['id'],p['price'],p['currency'],stamp,p['source']))
  check_alerts(c,p['id'],p['price'],stamp)
 return stamp

def check_alerts(c,pid,price,stamp):
 for a in c.execute('SELECT id FROM alerts WHERE product_id=? AND active=1 AND target>=?',(pid,price)).fetchall():
  c.execute('UPDATE alerts SET active=0,triggered_at=? WHERE id=?',(stamp,a['id']))
  c.execute('INSERT INTO events(alert_id,product_id,price,created_at) VALUES(?,?,?,?)',(a['id'],pid,price,stamp))

def add_alert(pid,target):
 if target<=0:raise ValueError('El precio objetivo debe ser positivo.')
 stamp=now()
 with connect() as c:
  p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
  if not p:raise ValueError('Primero consultá un producto real.')
  cur=c.execute('INSERT INTO alerts(product_id,target,created_at) VALUES(?,?,?)',(pid,target,stamp))
  # La alerta se evalúa inmediatamente con el último precio verificado.
  if p['last_price'] is not None:check_alerts(c,pid,p['last_price'],stamp)
  return cur.lastrowid

def products():
 with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM products ORDER BY last_seen DESC')]
def get(pid):
 with connect() as c:
  p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
  return dict(p) if p else None

def history(pid):
 with connect() as c:return [dict(r) for r in c.execute('SELECT price,observed_at,currency,source FROM observations WHERE product_id=? ORDER BY observed_at',(pid,))]
def alerts():
 with connect() as c:return [dict(r) for r in c.execute('SELECT a.*,p.title,p.currency,p.last_price FROM alerts a JOIN products p ON a.product_id=p.id ORDER BY a.id DESC')]
def events():
 with connect() as c:return [dict(r) for r in c.execute('SELECT e.*,p.title,p.currency FROM events e JOIN products p ON e.product_id=p.id ORDER BY e.id DESC LIMIT 50')]
def deactivate(aid):
 with connect() as c:c.execute('UPDATE alerts SET active=0 WHERE id=?',(aid,))
def stats(pid):
 rows=history(pid)
 if not rows:return None
 values=[r['price'] for r in rows]
 days=len({r['observed_at'][:10] for r in rows})
 return {'n':len(rows),'days':days,'min':min(values),'max':max(values),'avg':statistics.mean(values),'first':rows[0]['observed_at'],'last':rows[-1]['observed_at']}
