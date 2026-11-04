"""Run ONLY under dbus-run-session: real gdbus calls against an isolated fake store.
No method is sent to the user's real permission store; no browser is launched.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

if not os.environ.get('KINECT_PRIVATE_BUS_TEST'):
    raise SystemExit('Use dbus-run-session -- env KINECT_PRIVATE_BUS_TEST=1 python3 -B tests/v19/test_portal_integration.py -v')

ROOT=Path(__file__).resolve().parents[2]
SERVICE='org.freedesktop.impl.portal.PermissionStore'
OBJECT='/org/freedesktop/impl/portal/PermissionStore'
APP='org.mozilla.firefox'
OTHER='org.example.UnrelatedCameraApp'
DBusGMainLoop(set_as_default=True)
bus=dbus.SessionBus()
# Never replace an existing service, even if the test was accidentally given a used bus.
if bus.name_has_owner(SERVICE):
    raise SystemExit('Refusing to test on a bus with an existing permission store.')
name=dbus.service.BusName(SERVICE,bus,do_not_queue=True)


class Store(dbus.service.Object):
    def reset(self):
        self.permissions={APP:['no'],OTHER:['no']}
        self.deleted=[]
        self.fail=False
        self.resource_missing=False
        self.race=False
        self.no_op=False
        self.queries=0

    @dbus.service.method(SERVICE,in_signature='sss',out_signature='as')
    def GetPermission(self,table,resource,app):
        if str(table)!='devices' or str(resource)!='camera':
            raise dbus.exceptions.DBusException('wrong resource',name='org.freedesktop.DBus.Error.InvalidArgs')
        self.queries+=1
        if self.fail:
            raise dbus.exceptions.DBusException('simulated outage',name='org.freedesktop.DBus.Error.Failed')
        if self.resource_missing:
            raise dbus.exceptions.DBusException('No entry for camera',name='org.freedesktop.portal.Error.NotFound')
        if self.race and self.queries==2:
            self.permissions[APP]=['yes']
        return dbus.Array(self.permissions.get(str(app),[]),signature='s')

    @dbus.service.method(SERVICE,in_signature='sss',out_signature='')
    def DeletePermission(self,table,resource,app):
        if (str(table),str(resource),str(app))!=('devices','camera',APP):
            raise dbus.exceptions.DBusException('wrong reset target',name='org.freedesktop.DBus.Error.InvalidArgs')
        self.deleted.append(str(app))
        if not self.no_op:
            self.permissions.pop(str(app),None)


store=Store(bus,OBJECT)
store.reset()


def run_helper(*args):
    def invoke():
        return subprocess.run(['/usr/bin/python3','-B','-I',str(ROOT/'v19/kinect-facecam-firefox-permission-v19.py'),*args],
                              capture_output=True,text=True,timeout=20,
                              env=dict(os.environ,XDG_RUNTIME_DIR=test_runtime_dir))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(invoke)
        loop=GLib.MainLoop()
        def done():
            if task.done():
                loop.quit()
                return False
            return True
        GLib.timeout_add(10,done)
        loop.run()
        result=task.result()
    return result.returncode,json.loads(result.stdout)


class PrivateBusTests(unittest.TestCase):
    def setUp(self):
        global test_runtime_dir
        store.reset()
        self.runtime = tempfile.TemporaryDirectory(prefix='kinect-private-bus-test-')
        self.addCleanup(self.runtime.cleanup)
        test_runtime_dir = self.runtime.name

    def test_read_only_denial_does_not_mutate(self):
        code,result=run_helper('--check')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'denied')
        self.assertEqual(store.deleted,[])

    def test_explicit_reset_removes_only_firefox_camera_decision(self):
        code,result=run_helper('--reset-blocking','--consent')
        self.assertEqual(code,0)
        self.assertTrue(result['changed'])
        self.assertEqual(result['status'],'unset')
        self.assertEqual(store.deleted,[APP])
        self.assertEqual(store.permissions[OTHER],['no'])

    def test_reset_without_consent_is_rejected(self):
        code,result=run_helper('--reset-blocking')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'error')
        self.assertEqual(store.permissions[APP],['no'])
        self.assertEqual(store.deleted,[])

    def test_valid_allow_is_never_deleted(self):
        store.permissions[APP]=['yes']
        code,result=run_helper('--reset-blocking','--consent')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'allowed')
        self.assertFalse(result['changed'])
        self.assertEqual(store.deleted,[])

    def test_unset_app_is_valid_first_use(self):
        store.permissions.pop(APP)
        code,result=run_helper('--check')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'unset')
        self.assertEqual(store.deleted,[])

    def test_missing_resource_is_valid_first_use(self):
        store.resource_missing=True
        code,result=run_helper('--check')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'unset')

    def test_service_error_is_not_mistaken_for_unset(self):
        store.fail=True
        code,result=run_helper('--check')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'error')
        self.assertEqual(store.deleted,[])

    def test_new_allow_is_preserved_when_decision_changes(self):
        store.race=True
        code,result=run_helper('--reset-blocking','--consent')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'allowed')
        self.assertEqual(store.deleted,[])

    def test_ask_blocker_can_be_reset_with_consent(self):
        store.permissions[APP]=['ask']
        code,result=run_helper('--reset-blocking','--consent')
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'unset')

    def test_reset_is_checked_and_not_retried_blindly(self):
        store.no_op=True
        code,result=run_helper('--reset-blocking','--consent')
        self.assertNotEqual(code,0)
        self.assertEqual(result['status'],'error')
        self.assertEqual(store.deleted,[APP])


if __name__=='__main__':unittest.main()
