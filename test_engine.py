import os,tempfile,unittest
class TestEngine(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();os.environ['SMARTWAIT_DB']=os.path.join(self.tmp.name,'test.db')
  import engine
  self.e=engine;engine.init()
 def tearDown(self):self.tmp.cleanup()
 def test_alert_immediate_and_history(self):
  p={'id':'MLA1234567890','title':'Test real source stub','url':'https://example.com','price':100.,'currency':'ARS','source':'test stub'}
  self.e.save(p);self.assertEqual(self.e.stats(p['id'])['n'],1)
  aid=self.e.add_alert(p['id'],120)
  self.assertTrue(next(x for x in self.e.alerts() if x['id']==aid)['triggered_at'])
  self.assertEqual(len(self.e.events()),1)
 def test_alert_later(self):
  p={'id':'MLA1234567890','title':'Test','url':'https://example.com','price':100.,'currency':'ARS','source':'test stub'}
  self.e.save(p);aid=self.e.add_alert(p['id'],80)
  self.assertFalse(next(x for x in self.e.alerts() if x['id']==aid)['triggered_at'])
  p['price']=79.;self.e.save(p)
  self.assertTrue(next(x for x in self.e.alerts() if x['id']==aid)['triggered_at'])
 def test_bad_id(self):self.assertIsNone(self.e.ml_id('not an item'))
if __name__=='__main__':unittest.main()
