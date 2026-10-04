import os
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from storage import Storage
import billing
class Obj(dict):
    __getattr__ = dict.__getitem__
class BillingTests(unittest.TestCase):
    def test_verified_entitlement_requires_paid_live_matching_price(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Storage(folder+'/db')
            db.register('alice','strongpassword123')
            with db.connect() as conn:
                conn.execute('INSERT INTO memberships(username,customer) VALUES (?,?)',('alice','cus_alice'))
            item=Obj(price=Obj(id=billing.PRICE),current_period_end=9999999999)
            sub=Obj(status='active',livemode=True,latest_invoice=Obj(status='paid'),items=Obj(data=[item]))
            fake=SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(list=lambda _:SimpleNamespace(data=[sub]))))
            with patch('billing.client',return_value=fake):
                self.assertTrue(billing.refresh(db,'cus_alice'))
                for changes in ({'status':'past_due'},{'latest_invoice':Obj(status='open')},{'livemode':False}):
                    original=dict(sub)
                    sub.update(changes)
                    self.assertFalse(billing.refresh(db,'cus_alice'))
                    sub.clear(); sub.update(original)
                item.price.id='price_other_application'
                self.assertFalse(billing.refresh(db,'cus_alice'))
    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertFalse(billing.allowed(None,'alice'))
if __name__=='__main__': unittest.main()
