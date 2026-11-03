import os,re,time,streamlit as st,pandas as pd
import oauth
from engine import init,ml_id,fetch_ml,save,add_alert,products,get,history,stats,alerts,events,deactivate
st.set_page_config(page_title='SmartWait | Price Intelligence',page_icon='🛍️',layout='centered')
init()
st.markdown('''<style>.block-container{max-width:860px;padding-top:2rem}.stChatMessage{border-radius:14px} .stButton button{border-radius:9px}</style>''',unsafe_allow_html=True)
if 'messages' not in st.session_state:st.session_state.messages=[{'role':'assistant','content':'¡Hola! Soy **SmartWait**. Consulto precios verificables de publicaciones de Mercado Libre y construyo un historial real desde que las seguimos. Pegá un enlace o ID `MLA...` para empezar. Si no tengo datos, te lo digo.'}]
if 'current' not in st.session_state:st.session_state.current=None
if 'last_check' not in st.session_state:st.session_state.last_check=0
if 'token' not in st.session_state:st.session_state.token=''
settings=oauth.config()
if settings:oauth.callback(settings)
st.session_state.token=oauth.access_token(settings) if settings else ''

def money(value,currency='ARS'):
 return f'{currency} {value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def show_graph(pid):
 h=history(pid)
 if len(h)<2:st.info('Solo hay una medición. Necesito al menos dos precios registrados para dibujar una evolución real.');return
 df=pd.DataFrame(h);df['Fecha']=pd.to_datetime(df['observed_at'],utc=True);df=df.set_index('Fecha')
 st.line_chart(df['price'],y_label='Precio registrado',x_label='Fecha de consulta')
 st.caption('Mediciones reales capturadas por SmartWait; no representan todos los cambios ocurridos entre consultas.')
def render_message(m):
 st.markdown(m['content'])
 if m.get('graph'):show_graph(m['graph'])

def response(q):
 text=q.lower().strip();pid=ml_id(q)
 if pid:
  try:
   p=fetch_ml(pid,st.session_state.token);stamp=save(p);st.session_state.current=pid
   return {'role':'assistant','content':f'Encontré **{p["title"]}**.\n\n**Precio verificado:** {money(p["price"],p["currency"])}\n\n**Fuente:** [Mercado Libre]({p["url"]}) · Consulta UTC: {stamp}\n\nRegistré esta medición en tu historial. Podés pedirme **gráfico**, **historial**, **alerta a 100000** o **actualizar precio**. No afirmaré que es una oferta sin datos suficientes.'}
  except ValueError as exc:return {'role':'assistant','content':f'No pude obtener un precio verificado: **{exc}**'}
 pid=st.session_state.current
 if not pid:return {'role':'assistant','content':'Para darte información real necesito identificar la publicación exacta. Pegá un enlace o ID de Mercado Libre Argentina que empiece por `MLA`. No voy a adivinar el producto ni su precio.'}
 p=get(pid)
 if not p:return {'role':'assistant','content':'No tengo datos guardados para ese producto.'}
 if any(w in text for w in ('actualiz','refresc','consultá de nuevo','precio ahora','precio actual')):
  try:
   new=fetch_ml(pid,st.session_state.token);save(new)
   return {'role':'assistant','content':f'Precio recién verificado: **{money(new["price"],new["currency"])}**. Registré una nueva observación. Fuente: [Mercado Libre]({new["url"]}).'}
  except ValueError as exc:return {'role':'assistant','content':f'No pude actualizar: {exc}. **No voy a presentar el último precio guardado como si fuera actual.**'}
 if any(w in text for w in ('gráfic','grafico','evolución','evolucion','curva')):
  return {'role':'assistant','content':f'Este es el historial registrado para **{p["title"]}**:', 'graph':pid}
 if any(w in text for w in ('historial','mínimo','minimo','máximo','maximo','promedio','conviene','comprar','esperar','barato','caro','tendencia')):
  s=stats(pid)
  if s['n']<2 or s['days']<2:
   return {'role':'assistant','content':f'Último precio registrado de **{p["title"]}**: **{money(p["last_price"],p["currency"])}** (UTC {p["last_seen"]}).\n\n**Todavía no tengo historial temporal suficiente** para determinar si conviene comprar o esperar. Hay {s["n"]} medición(es) en {s["days"]} día(s). Volvé a consultar en otros días.'}
  return {'role':'assistant','content':f'**{p["title"]}**\n\n- Último precio guardado: **{money(p["last_price"],p["currency"])}** ({p["last_seen"]} UTC)\n- Mínimo observado: {money(s["min"],p["currency"])}\n- Máximo observado: {money(s["max"],p["currency"])}\n- Promedio observado: {money(s["avg"],p["currency"])}\n- Muestra: {s["n"]} observaciones en {s["days"]} días.\n\nEstos valores describen **solo los precios que SmartWait registró**. No predicen precios futuros ni garantizan que sea el mejor momento para comprar.'}
 if 'alerta' in text or 'avis' in text:
  nums=re.findall(r'\d[\d.,]*',text)
  if not nums:return {'role':'assistant','content':'Decime un objetivo, por ejemplo: **alerta a 120000**. La alerta se guarda en el momento y se verifica con cada actualización.'}
  raw=nums[-1].replace('.','').replace(',','.')
  try:
   target=float(raw);aid=add_alert(pid,target)
   a=next(a for a in alerts() if a['id']==aid)
   status='**Ya se cumplió** con el último precio registrado.' if a['triggered_at'] else '**Activa**, esperando una nueva verificación.'
   return {'role':'assistant','content':f'🔔 Alerta **#{aid}** guardada para **{p["title"]}** cuando el precio sea ≤ **{money(target,p["currency"])}**. {status}\n\nImportante: las alertas se muestran dentro de SmartWait; esta versión no envía emails ni funciona cuando Colab está apagado.'}
  except (ValueError,OverflowError) as exc:return {'role':'assistant','content':f'No pude crear la alerta: {exc}'}
 return {'role':'assistant','content':f'Seguimos con **{p["title"]}**. Puedo **actualizar precio**, mostrar **historial**, generar **gráfico** o crear **alerta a 120000**. Si querés otro producto, pegá su enlace o ID exacto.'}

st.title('🛍️ SmartWait')
st.caption('Precios verificables · Historial propio · Alertas inmediatas · Sin precios inventados')
with st.sidebar:
 st.header('Configuración')
 if not settings:
  st.error('Faltan MELI_CLIENT_ID, MELI_CLIENT_SECRET o MELI_REDIRECT_URI en Secrets.')
 elif st.session_state.token:
  st.success('Mercado Libre conectado')
  if st.button('Desconectar'):
   for key in ('meli_access_token','meli_refresh_token','meli_expires_at'):st.session_state.pop(key,None)
   st.session_state.token=''
   st.rerun()
 else:
  st.link_button('Conectar con Mercado Libre',oauth.authorization_url(settings))
  st.info('Autorizá tu cuenta para consultar publicaciones. La conexión dura mientras esta sesión siga activa.')
 st.divider()
 st.subheader('Seguimiento')
 known=products()
 if known:
  selected=st.selectbox('Producto seguido',known,format_func=lambda p:p['title'][:60],index=None,placeholder='Seleccioná un producto')
  if selected and st.button('Usar en el chat'):
   st.session_state.current=selected['id'];st.success('Producto seleccionado')
  st.caption(f'{len(known)} publicaciones registradas')
 else:st.caption('Todavía no seguís productos.')
 st.divider()
 st.subheader('Alertas')
 for a in alerts()[:30]:
  status='🟢 Cumplida' if a['triggered_at'] else ('🔔 Activa' if a['active'] else 'Cancelada')
  st.write(f'#{a["id"]} · {a["title"][:35]} · {money(a["target"],a["currency"])} · {status}')
  if a['active'] and st.button('Cancelar',key=f'cancel_{a["id"]}'):
   deactivate(a['id']);st.rerun()
 st.divider()
 if st.button('Descargar historial CSV'):
  rows=[]
  for p in products():
   for h in history(p['id']):rows.append({'producto':p['title'],'id':p['id'],**h})
  if rows:st.download_button('Guardar CSV',pd.DataFrame(rows).to_csv(index=False).encode('utf-8-sig'),file_name='smartwait_historial.csv',mime='text/csv')
  else:st.info('Aún no hay observaciones.')

@st.fragment(run_every='60s')
def notifications():
 # Actualización automática solo mientras la app está abierta y el token es válido.
 if st.session_state.token and time.time()-st.session_state.get('last_check',0)>300:
  st.session_state.last_check=time.time()
  for p in products()[:5]:
   try:save(fetch_ml(p['id'],st.session_state.token))
   except (ValueError,Exception):pass  # Mantener el último dato fechado; no fingir actualización.
 ev=events()
 if ev:
  recent=[e for e in ev if e['id']>st.session_state.get('seen_event',0)]
  if recent:
   st.success(f'🔔 {len(recent)} alerta(s) alcanzaron su objetivo. Mirá el panel lateral.')
   st.session_state.seen_event=max(e['id'] for e in ev)
notifications()
for m in st.session_state.messages:
 with st.chat_message(m['role']):render_message(m)
if prompt:=st.chat_input('Preguntá por un producto o pegá un enlace de Mercado Libre...'):
 st.session_state.messages.append({'role':'user','content':prompt})
 with st.chat_message('user'):st.markdown(prompt)
 with st.chat_message('assistant'):
  with st.spinner('Consultando información verificable...'):
   answer=response(prompt)
  render_message(answer)
 st.session_state.messages.append(answer)
 st.rerun()
