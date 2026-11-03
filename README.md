# SmartWait LIVE 3.0

## Qué es
Chatbot de seguimiento de publicaciones **reales** de Mercado Libre Argentina. Consulta la API oficial con un token OAuth válido, guarda observaciones con fecha UTC en SQLite, dibuja únicamente históricos realmente registrados y permite alertas inmediatas dentro de la aplicación.

**No incluye precios ficticios.** No ofrece un historial anterior al momento de empezar a registrar. No predice el futuro. La API puede negar el acceso a publicaciones ajenas o a búsquedas según permisos y políticas. El precio final de compra puede variar por promociones, ubicación, envío y cuenta del comprador.

## Google Colab

1. Subí `smartwait_live.zip` al panel de archivos de Colab.
2. Ejecutá en una celda:

```python
!unzip -o /content/smartwait_live.zip -d /content/
!pip -q install -r /content/smartwait_live/requirements.txt
```

3. Detené versiones anteriores y arrancá la nueva:

```python
!pkill -f 'streamlit run' || true
!nohup streamlit run /content/smartwait_live/app.py --server.port 8501 --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false > /content/smartwait_live/streamlit.log 2>&1 &
```

4. En otra celda:

```python
from google.colab import output
print(output.eval_js('google.colab.kernel.proxyPort(8501)'))
```

5. Abrí la URL generada, configurá tu token OAuth y pegá una URL de publicación de Mercado Libre Argentina o su ID MLA.

## Credenciales

Creá una aplicación en el portal oficial de desarrolladores de Mercado Libre y obtené un token OAuth autorizado. No compartas tokens por chat. El token pegado en el sidebar se conserva solo en la sesión de Streamlit; no se escribe a SQLite. Para producción, usar un gestor de secretos y autorización por usuario. Si Mercado Libre niega el permiso, SmartWait **no inventará un precio**.

Documentación oficial:
- https://developers.mercadolibre.com.ar/autenticacion-y-autorizacion
- https://developers.mercadolibre.com.ar/api-de-precios

## Limitaciones explícitas

- Las alertas se crean y verifican inmediatamente usando el último precio registrado. La aplicación vuelve a consultar hasta 5 productos cada 5 minutos mientras el navegador permanece conectado, hay token y Colab sigue funcionando. No hay notificaciones por correo o push.
- La app no puede garantizar disponibilidad en tiempo real, ni histórico anterior, ni que Mercado Libre autorice cada publicación. No mezcla monedas.
- **Colab es temporal:** el archivo SQLite se pierde cuando se elimina el entorno de ejecución. Exportá el CSV periódicamente. Para producción, alojar en un servidor persistente con base de datos administrada, worker programado y sistema de alertas externo.
- Una aplicación de producción necesita además OAuth completo con refresh token, manejo de cuotas, pruebas de integración, autenticación de usuarios y monitoreo.

## Estructura
- `app.py`: chat, interfaz y alertas.
- `engine.py`: API, validación, persistencia y lógica de alertas.
- `requirements.txt`: dependencias.
- `test_engine.py`: pruebas locales sin red.
