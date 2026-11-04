/* Kinect-only libwdi frontend. No arbitrary VID/PID or destination arguments. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlobj.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include "libwdi.h"

static int target(unsigned short vid, unsigned short pid, BOOL composite, int audio) {
    return vid == 0x045e && !composite && (audio ? pid == 0x02ad : (pid == 0x02ae || pid == 0x02bf));
}

static int directory(wchar_t *path, const wchar_t *suffix) {
    if (wcslen(path) + wcslen(suffix) >= MAX_PATH) return 0;
    wcscat(path, suffix);
    if (!CreateDirectoryW(path, NULL) && GetLastError() != ERROR_ALREADY_EXISTS) return 0;
    DWORD attrs = GetFileAttributesW(path);
    return attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_DIRECTORY) && !(attrs & FILE_ATTRIBUTE_REPARSE_POINT);
}

int wmain(int argc, wchar_t **argv) {
    if (argc == 2 && !wcscmp(argv[1], L"--self-test")) {
        if (!target(0x045e,0x02ae,FALSE,0) || !target(0x045e,0x02bf,FALSE,0) ||
            !target(0x045e,0x02ad,FALSE,1) || target(0x045e,0x02ad,FALSE,0) ||
            target(0x045e,0x02bb,FALSE,1) || target(0x045e,0x02b0,FALSE,0) ||
            target(0x1234,0x02ae,FALSE,0) || target(0x045e,0x02ae,TRUE,0)) return 1;
        return wdi_is_driver_supported(WDI_LIBUSBK, NULL) ? 0 : 22;
    }
    int check = argc == 2 && !wcscmp(argv[1], L"--check");
    int audio = argc == 3 && !wcscmp(argv[1], L"--install-audio");
    int camera = argc == 3 && !wcscmp(argv[1], L"--install-camera");
    if (!check && (!(audio || camera) || wcscmp(argv[2], L"--consent"))) return 2;
    if (!check && !IsUserAnAdmin()) return 23;
    struct wdi_device_info *list = NULL, *selected = NULL;
    struct wdi_options_create_list options = {0};
    options.list_all = TRUE; options.trim_whitespaces = TRUE;
    int rc = wdi_create_list(&list, &options);
    if (rc) return 100 - rc;
    int count = 0, camera_count = 0, audio_count = 0, camera_ready = 0, audio_ready = 0;
    for (struct wdi_device_info *d = list; d; d = d->next) {
        int ready = d->driver && !_stricmp(d->driver, "libusbK");
        if (target(d->vid,d->pid,d->is_composite,0)) { camera_count++; camera_ready += ready; }
        if (target(d->vid,d->pid,d->is_composite,1)) { audio_count++; audio_ready += ready; }
        if (target(d->vid,d->pid,d->is_composite,audio)) { count++; selected = d; }
    }
    if (check) {
        printf("{\"camera_count\":%d,\"camera_ready\":%d,\"audio_count\":%d,\"audio_ready\":%d}\n",camera_count,camera_ready,audio_count,audio_ready);
        wdi_destroy_list(list); return 0;
    }
    if (count != 1) { wdi_destroy_list(list); return count ? 21 : 20; }
    if (selected->driver && !_stricmp(selected->driver,"libusbK")) { wdi_destroy_list(list); return 0; }
    if (!wdi_is_driver_supported(WDI_LIBUSBK,NULL)) { wdi_destroy_list(list); return 22; }
    wchar_t path[MAX_PATH] = {0}; PWSTR program_files = NULL;
    if (FAILED(SHGetKnownFolderPath(&FOLDERID_ProgramFiles,0,NULL,&program_files))) { wdi_destroy_list(list); return 24; }
    int ok = wcslen(program_files) < MAX_PATH;
    if (ok) wcscpy(path,program_files);
    CoTaskMemFree(program_files);
    if (!ok || !directory(path,L"\\Kinect Webcam") || !directory(path,L"\\drivers") ||
        !directory(path,audio ? L"\\audio-loader" : L"\\camera")) { wdi_destroy_list(list); return 24; }
    char utf8[MAX_PATH*4];
    if (!WideCharToMultiByte(CP_UTF8,0,path,-1,utf8,sizeof(utf8),NULL,NULL)) { wdi_destroy_list(list); return 24; }
    struct wdi_options_prepare_driver prepare = {0}; prepare.driver_type = WDI_LIBUSBK;
    prepare.vendor_name = "Kinect Webcam";
    struct wdi_options_install_driver install = {0}; install.pending_install_timeout = 120000;
    rc = wdi_prepare_driver(selected,utf8,"kinect.inf",&prepare);
    if (!rc) rc = wdi_install_driver(selected,utf8,"kinect.inf",&install);
    wdi_destroy_list(list);
    return rc ? 100 - rc : 0;
}
