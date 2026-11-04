"""The GUI requests elevation for a bundled helper restricted to Kinect USB IDs."""
import ctypes
from ctypes import wintypes
import subprocess
import sys
from common import native_dir


def elevate(helper, purpose):
    class ExecuteInfo(ctypes.Structure):
        _fields_=[('cbSize',wintypes.DWORD),('fMask',wintypes.ULONG),('hwnd',wintypes.HWND),
                  ('lpVerb',wintypes.LPCWSTR),('lpFile',wintypes.LPCWSTR),('lpParameters',wintypes.LPCWSTR),
                  ('lpDirectory',wintypes.LPCWSTR),('nShow',ctypes.c_int),('hInstApp',wintypes.HINSTANCE),
                  ('lpIDList',ctypes.c_void_p),('lpClass',wintypes.LPCWSTR),('hkeyClass',wintypes.HKEY),
                  ('dwHotKey',wintypes.DWORD),('hIcon',wintypes.HANDLE),('hProcess',wintypes.HANDLE)]
    shell=ctypes.WinDLL('shell32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    shell.ShellExecuteExW.argtypes=[ctypes.POINTER(ExecuteInfo)];shell.ShellExecuteExW.restype=wintypes.BOOL
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];kernel.GetExitCodeProcess.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    info=ExecuteInfo();info.cbSize=ctypes.sizeof(info);info.fMask=0x40;info.lpVerb='runas'
    info.lpFile=str(helper);info.lpDirectory=str(helper.parent)
    info.lpParameters=subprocess.list2cmdline(['--install-'+purpose,'--consent']);info.nShow=0
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        error=ctypes.get_last_error()
        if error==1223:raise RuntimeError('Yönetici onayı iptal edildi; sürücü kurulmadı.')
        raise ctypes.WinError(error)
    try:
        if not info.hProcess or kernel.WaitForSingleObject(info.hProcess,0xffffffff)!=0:
            raise RuntimeError('Sürücü kurulum sonucu alınamadı; aygıt durumunu yeniden denetle.')
        code=wintypes.DWORD()
        if not kernel.GetExitCodeProcess(info.hProcess,ctypes.byref(code)):raise ctypes.WinError(ctypes.get_last_error())
        return code.value
    finally:
        if info.hProcess:kernel.CloseHandle(info.hProcess)


def install(purpose):
    if purpose not in ('camera','audio'):raise ValueError('Geçersiz Kinect kurulum adımı.')
    if sys.platform!='win32':raise RuntimeError('Sürücü kurulumu yalnızca Windows içindir.')
    helper=native_dir()/'kinect-driver.exe'
    if not helper.is_file():raise RuntimeError('Paketin sürücü bileşeni eksik; tam Windows paketini yeniden indir.')
    code=elevate(helper.resolve(),purpose)
    if code:
        messages={20:'İlgili Kinect USB aygıtı bulunamadı. Güç/USB bağlantısını denetle. Ses adımı yalnızca ham 045e:02ad aygıtı içindir.',
                  21:'Birden fazla eşleşen Kinect bulundu. Yalnızca hazırlayacağın Kinect bağlı kalsın.',
                  22:'Paket içindeki libusbK sürücüsü kullanılamıyor.',23:'Yönetici onayı alınamadı.',
                  24:'Korumalı sürücü klasörü hazırlanamadı.',114:'Kurulum kullanıcı tarafından iptal edildi.',
                  119:'Windows sürücü imza ilkesi kuruluma izin vermedi. Koruma ayarlarını kapatmayın.'}
        raise RuntimeError(messages.get(code,f'Sürücü kurulumu tamamlanamadı (kod {code}). Yeniden başlatma gerekebilir; hazır olarak işaretlenmedi.'))
    return 'Kinect sürücüsü hazırlandı. Gerekirse USB’yi çıkarıp tak; ardından kamerayı başlat.'
